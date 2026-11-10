"""Objectify contract and isolation tests. No production endpoint is contacted."""
import copy
from email.message import Message
import hashlib
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
SERVER = HERE / "server.py"
spec = importlib.util.spec_from_file_location("objectify_server", SERVER)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeResponse:
    def __init__(self, data, url, status=200, content_type="application/json"):
        self.body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.stream = io.BytesIO(self.body)
        self.url = url
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def geturl(self):
        return self.url

    def read(self, n):
        return self.stream.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, data):
        self.data = data
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if isinstance(self.data, Exception):
            raise self.data
        if isinstance(self.data, FakeResponse):
            return self.data
        return FakeResponse(self.data, request.full_url)


class ObjectifyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.api = {
            "openapi": "3.0.3",
            "info": {"title": "Synthetic test contract; not Objectify's real schema", "version": "test"},
            "paths": {
                "/back": {"get": {"operationId": "syntheticBackend", "parameters": []}},
                "/account/obj_acc": {"get": {"operationId": "syntheticAccount", "parameters": [
                    {"name": "test_account", "in": "query", "required": True,
                     "schema": {"type": "string"}}]}},
                "/account/obj_acc/epg": {"get": {"operationId": "syntheticEpg", "parameters": []}},
                "/getAllSink": {"get": {"operationId": "syntheticList", "parameters": []}},
            },
        }
        self.config = {
            "enabled": True,
            "context": {"customer_id": "test-customer-a", "cluster_id": "test-cluster-a", "environment": "test"},
            "base_url": "https://objectify.invalid/api/v1",
            "authentication": {"type": "bearer", "token_env": "SDS_OBJECTIFY_TEST_TOKEN"},
            "tls": {"ca_file": None},
            "contract": {"reviewed": True, "openapi_file": "openapi.json", "openapi_sha256": "",
                         "reviewed_by": "synthetic-reviewer", "reviewed_on": "2026-01-01",
                         "upstream_context_scoped": True, "listing_scope_verified": False},
            "limits": {"timeout_seconds": 2, "max_response_bytes": 1024, "max_records": 2},
            "operations": {
                "objectify_get_account": {
                    "method": "GET", "path": "/account/obj_acc", "operation_id": "syntheticAccount",
                    "read_only_verified": True,
                    "parameters": {"test_account": {"type": "string", "required": True,
                                                     "max_length": 64, "pattern": "[A-Za-z0-9_.-]+"}},
                    "response": {"records_pointer": "", "many": False,
                                 "fields": {"account_id": {"pointer": "/id", "type": "string", "required": True,
                                                           "max_length": 64, "pattern": "[A-Za-z0-9_.-]+"},
                                            "used_bytes": {"pointer": "/usage", "type": "integer"}},
                                 "scope_checks": [{"pointer": "/customer", "context_field": "customer_id"},
                                                  {"pointer": "/cluster", "context_field": "cluster_id"}]},
                }
            },
        }
        self.args = {"customer_id": "test-customer-a", "cluster_id": "test-cluster-a",
                     "parameters": {"test_account": "acc-1"}}
        self.record = {"id": "acc-1", "usage": 42, "customer": "test-customer-a", "cluster": "test-cluster-a",
                       "secret_key": "must-not-leak", "nested": {"password": "also-secret"}, "email": "private@example.invalid"}
        self.env = mock.patch.dict(os.environ, {"SDS_OBJECTIFY_TEST_TOKEN": "synthetic-token-for-tests"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def write(self):
        raw = json.dumps(self.api).encode()
        (self.path / "openapi.json").write_bytes(raw)
        self.config["contract"]["openapi_sha256"] = hashlib.sha256(raw).hexdigest()
        path = self.path / "config.json"
        path.write_text(json.dumps(self.config))
        return path

    def adapter(self, data=None):
        adapter = mod.Objectify(mod.load_config(self.write()))
        adapter._opener = FakeOpener(self.record if data is None else data)
        return adapter

    def assert_config_rejected(self):
        with self.assertRaises(mod.ConfigError):
            mod.load_config(self.write())

    def test_shipped_default_exposes_only_local_status(self):
        adapter = mod.Objectify(mod.load_config(HERE / "config.example.json"))
        self.assertEqual([t["name"] for t in adapter.tools()], ["objectify_status"])
        with mock.patch.object(urllib.request, "build_opener", side_effect=AssertionError("no network")):
            self.assertFalse(adapter.call("objectify_status", {})["network_check_performed"])
            with self.assertRaises(mod.CallError):
                adapter.call("objectify_get_account", self.args)

    def test_success_projects_only_explicit_scalar_fields(self):
        result = self.adapter().call("objectify_get_account", self.args)
        self.assertEqual(result["record"], {"account_id": "acc-1", "used_bytes": 42})
        self.assertNotIn("secret", json.dumps(result))
        self.assertNotIn("private@example", json.dumps(result))

    def test_customer_mismatch_does_not_send_request(self):
        adapter = self.adapter()
        self.args["customer_id"] = "test-customer-b"
        with self.assertRaises(mod.CallError):
            adapter.call("objectify_get_account", self.args)
        self.assertEqual(adapter._opener.requests, [])

    def test_cluster_mismatch_does_not_send_request(self):
        adapter = self.adapter()
        self.args["cluster_id"] = "test-cluster-b"
        with self.assertRaises(mod.CallError):
            adapter.call("objectify_get_account", self.args)
        self.assertEqual(adapter._opener.requests, [])

    def test_response_scope_mismatch_is_refused(self):
        self.record["customer"] = "test-customer-b"
        with self.assertRaises(mod.CallError):
            self.adapter().call("objectify_get_account", self.args)

    def test_response_without_scope_evidence_is_refused(self):
        del self.record["cluster"]
        with self.assertRaises(mod.CallError):
            self.adapter().call("objectify_get_account", self.args)

    def test_write_methods_cannot_be_enabled(self):
        for method in ("POST", "PATCH", "DELETE", "PUT", "get"):
            with self.subTest(method=method):
                self.config["operations"]["objectify_get_account"]["method"] = method
                self.assert_config_rejected()

    def test_arbitrary_operation_cannot_be_enabled(self):
        self.config["operations"]["objectify_create_account"] = copy.deepcopy(self.config["operations"]["objectify_get_account"])
        self.assert_config_rejected()

    def test_parlay_and_path_substitution_cannot_be_enabled(self):
        for path in ("/account/parlay", "/account/{account_id}", "/account/obj_acc/modify", "https://evil.invalid/", "/back?x=1"):
            with self.subTest(path=path):
                self.config["operations"]["objectify_get_account"]["path"] = path
                self.assert_config_rejected()

    def test_plain_http_and_embedded_credentials_are_rejected(self):
        for url in ("http://objectify.invalid", "https://user:password@objectify.invalid", "https://objectify.invalid/?key=x", "https://objectify.invalid/#frag"):
            with self.subTest(url=url):
                self.config["base_url"] = url
                self.assert_config_rejected()

    def test_tls_cannot_be_disabled(self):
        self.config["tls"]["verify"] = False
        self.assert_config_rejected()

    def test_openapi_pin_detects_change(self):
        path = self.write()
        (self.path / "openapi.json").write_text('{"openapi":"3.0.3","paths":{}}')
        with self.assertRaises(mod.ConfigError):
            mod.load_config(path)

    def test_missing_operation_in_spec_is_rejected(self):
        del self.api["paths"]["/account/obj_acc"]
        self.assert_config_rejected()

    def test_operation_id_mismatch_is_rejected(self):
        self.config["operations"]["objectify_get_account"]["operation_id"] = "not-the-reviewed-operation"
        self.assert_config_rejected()

    def test_query_contract_mismatch_is_rejected(self):
        self.api["paths"]["/account/obj_acc"]["get"]["parameters"][0]["schema"]["type"] = "integer"
        self.assert_config_rejected()

    def test_get_does_not_replace_semantic_review(self):
        self.config["operations"]["objectify_get_account"]["read_only_verified"] = False
        self.assert_config_rejected()

    def test_upstream_rbac_must_be_verified(self):
        self.config["contract"]["upstream_context_scoped"] = False
        self.assert_config_rejected()

    def test_every_operation_requires_customer_and_cluster_response_checks(self):
        template = copy.deepcopy(self.config["operations"]["objectify_get_account"])
        for name, (path, _) in mod.OPERATIONS.items():
            for checks in ([], [{"pointer": "/customer", "context_field": "customer_id"}]):
                with self.subTest(name=name, checks=checks):
                    operation = copy.deepcopy(template)
                    operation.update(path=path, operation_id=self.api["paths"][path]["get"]["operationId"])
                    if name != "objectify_get_account":
                        operation["parameters"] = {}
                    operation["response"]["many"] = name == "objectify_list_accounts"
                    operation["response"]["scope_checks"] = checks
                    self.config["operations"] = {name: operation}
                    self.config["contract"]["listing_scope_verified"] = True
                    self.assert_config_rejected()

    def test_openapi_enum_is_enforced_beyond_broader_local_rule(self):
        self.api["paths"]["/account/obj_acc"]["get"]["parameters"][0]["schema"]["enum"] = ["acc-1"]
        adapter = self.adapter()
        self.args["parameters"]["test_account"] = "acc-2"
        with self.assertRaisesRegex(mod.CallError, "OpenAPI"):
            adapter.call("objectify_get_account", self.args)
        self.assertEqual(adapter._opener.requests, [])
        self.args["parameters"]["test_account"] = "acc-1"
        self.assertEqual(adapter.call("objectify_get_account", self.args)["record"]["account_id"], "acc-1")

    def test_openapi_string_lengths_and_pattern_are_all_enforced(self):
        schema = self.api["paths"]["/account/obj_acc"]["get"]["parameters"][0]["schema"]
        schema.update(minLength=5, maxLength=6, pattern="^acc-[0-9]+$")
        adapter = self.adapter()
        for value in ("x", "acc-123", "user-1"):
            with self.subTest(value=value):
                self.args["parameters"]["test_account"] = value
                with self.assertRaisesRegex(mod.CallError, "OpenAPI"):
                    adapter.call("objectify_get_account", self.args)
        self.assertEqual(adapter._opener.requests, [])
        self.args["parameters"]["test_account"] = "acc-1"
        self.assertEqual(adapter.call("objectify_get_account", self.args)["record"]["account_id"], "acc-1")

    def test_openapi_integer_bounds_are_enforced_beyond_local_rule(self):
        self.api["paths"]["/account/obj_acc"]["get"]["parameters"][0]["schema"] = {"type": "integer", "minimum": 3, "maximum": 5}
        self.config["operations"]["objectify_get_account"]["parameters"]["test_account"] = {
            "type": "integer", "required": True, "minimum": 0, "maximum": 100}
        adapter = self.adapter()
        for value in (2, 6):
            self.args["parameters"]["test_account"] = value
            with self.assertRaisesRegex(mod.CallError, "OpenAPI"):
                adapter.call("objectify_get_account", self.args)
        self.assertEqual(adapter._opener.requests, [])
        self.args["parameters"]["test_account"] = 3
        adapter.call("objectify_get_account", self.args)

    def test_unsupported_openapi_constraints_fail_closed(self):
        for schema in ({"type": "string", "minLength": -1},
                       {"type": "string", "enum": [True]},
                       {"type": "string", "nullable": True},
                       {"type": "string", "format": "date"},
                       {"type": "string", "allOf": [{"maxLength": 3}]},
                       {"type": "string", "pattern": "["}):
            with self.subTest(schema=schema):
                self.api["paths"]["/account/obj_acc"]["get"]["parameters"][0]["schema"] = schema
                self.assert_config_rejected()

    def test_configured_patterns_reject_backtracking_operators(self):
        for pattern in ("(a+)+$", "(a|aa)+$", "a+?", "a*+", "(?=a)a", r"(a)\1"):
            with self.subTest(pattern=pattern):
                with self.assertRaises(mod.ConfigError):
                    mod.compiled_pattern(pattern)
        self.api["paths"]["/account/obj_acc"]["get"]["parameters"][0]["schema"]["pattern"] = "(a+)+$"
        self.assert_config_rejected()
        del self.api["paths"]["/account/obj_acc"]["get"]["parameters"][0]["schema"]["pattern"]
        self.config["operations"]["objectify_get_account"]["parameters"]["test_account"]["pattern"] = "(a+)+$"
        self.assert_config_rejected()
        self.config["operations"]["objectify_get_account"]["parameters"]["test_account"]["pattern"] = ".+"
        self.config["operations"]["objectify_get_account"]["response"]["fields"]["account_id"]["pattern"] = "(a+)+$"
        self.assert_config_rejected()

    def test_small_pattern_language_matches_reference_for_control_free_values(self):
        patterns = ("", "^$", "a", "^a", "a$", "a?b*", "a+b", ".*", "[ab]{1,3}",
                    "[^a]+", "[a-z0-9-]+", r"\d{1,2}", r"\w+", r"\D", r"\W+",
                    r"\[a\]", "[a-c_]?", "a{0,}", "a{0}", "a*a*a*b", "[a-b-c]+")
        values = [""] + ["".join(chars) for size in range(1, 4)
                         for chars in itertools.product("ab1-é", repeat=size)] + ["[a]", " ", "_"]
        for pattern in patterns:
            checked = mod.compiled_pattern(pattern)
            for value in values:
                with self.subTest(pattern=pattern, value=value):
                    self.assertEqual(checked.matches(value), re.search(pattern, value, re.ASCII) is not None)
                    self.assertEqual(checked.matches(value, full=True), re.fullmatch(pattern, value, re.ASCII) is not None)

    def test_pattern_state_repetition_and_input_bounds(self):
        for pattern in ("a{257}", "a{256}b{256}", "a{3,2}", "a{,2}", "[", "[z-a]", "[]", r"\p{L}", r"\s", r"\S"):
            with self.subTest(pattern=pattern):
                with self.assertRaises(mod.ConfigError):
                    mod.compiled_pattern(pattern)
        self.assertTrue(mod.compiled_pattern("a{256}").matches("a" * 256, full=True))
        self.assertFalse(mod.compiled_pattern(".*").matches("a" * 257, full=True))
        self.assertFalse(mod.compiled_pattern(".").matches("\u2028", full=True))
        self.assertTrue(mod.compiled_pattern(".").matches("א", full=True))

    def test_hostile_value_uses_finite_state_matching(self):
        # Repeated ambiguous atoms make conventional backtracking exponential.
        # This permitted group-free expression is handled by the NFA directly.
        code = (
            "import importlib.util; "
            "s=importlib.util.spec_from_file_location('obj'," + repr(str(SERVER)) + "); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "assert not m.compiled_pattern('a*' * 100 + 'b').matches('a' * 256, full=True)"
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_local_parameter_and_output_enums_require_matching_scalar_types(self):
        rule = self.config["operations"]["objectify_get_account"]["parameters"]["test_account"]
        rule["enum"] = [True]
        self.assert_config_rejected()
        del rule["enum"]
        output = self.config["operations"]["objectify_get_account"]["response"]["fields"]["used_bytes"]
        output["enum"] = [True]
        self.assert_config_rejected()
        output["enum"] = [42]
        self.assertEqual(self.adapter().call("objectify_get_account", self.args)["record"]["used_bytes"], 42)
        self.assertFalse(mod.scalar_enum_matches(True, [1], "boolean"))
        self.assertFalse(mod.scalar_enum_matches(1, [True], "integer"))
        self.assertTrue(mod.scalar_enum_matches(1.0, [1], "number"))

    def test_string_enum_members_obey_supported_scalar_length(self):
        local = self.config["operations"]["objectify_get_account"]["parameters"]["test_account"]
        output = self.config["operations"]["objectify_get_account"]["response"]["fields"]["account_id"]
        upstream = self.api["paths"]["/account/obj_acc"]["get"]["parameters"][0]["schema"]
        for location, schema in (("local", local), ("output", output), ("upstream", upstream)):
            with self.subTest(schema_location=location):
                schema["enum"] = ["a" * 257]
                with self.assertRaisesRegex(mod.ConfigError, "256 characters"):
                    mod.load_config(self.write())
                del schema["enum"]

    def test_startup_caps_expanded_discovery_schema_with_unicode_escaping(self):
        values = ["א" * 128 + str(index) for index in range(100)]
        self.api["components"] = {"schemas": {"SharedId": {"type": "string", "enum": values}}}
        self.api["paths"]["/account/obj_acc"]["get"]["parameters"] = [
            {"name": "account_%d" % index, "in": "query", "required": True,
             "schema": {"$ref": "#/components/schemas/SharedId"}}
            for index in range(4)
        ]
        self.config["operations"]["objectify_get_account"]["parameters"] = {
            "account_%d" % index: {"type": "string", "required": True, "max_length": 256, "pattern": ".*"}
            for index in range(4)
        }
        with self.assertRaisesRegex(mod.ConfigError, "Tool discovery exceeds 256 KiB"):
            mod.load_config(self.write())

    def test_request_pattern_work_is_preflighted_before_matching_or_network(self):
        self.api["paths"]["/account/obj_acc"]["get"]["parameters"] = [
            {"name": "account_%d" % index, "in": "query", "required": True, "schema": {"type": "string"}}
            for index in range(12)
        ]
        self.config["operations"]["objectify_get_account"]["parameters"] = {
            "account_%d" % index: {"type": "string", "required": True, "max_length": 256,
                                   "pattern": "a{0,256}b{0,254}"}
            for index in range(12)
        }
        self.args["parameters"] = {"account_%d" % index: "a" * 256 for index in range(12)}
        adapter = self.adapter()
        with mock.patch.object(mod.LinearPattern, "matches", side_effect=AssertionError("Must preflight before matching")):
            with self.assertRaisesRegex(mod.CallError, "Validation work budget exceeded"):
                adapter.call("objectify_get_account", self.args)
        self.assertEqual(adapter._opener.requests, [])

    def test_local_openapi_ref_preserves_constraints_and_external_ref_is_refused(self):
        self.api["components"] = {"schemas": {"AccountId": {"type": "string", "enum": ["acc-1"]}}}
        parameter = self.api["paths"]["/account/obj_acc"]["get"]["parameters"][0]
        parameter["schema"] = {"$ref": "#/components/schemas/AccountId"}
        adapter = self.adapter()
        self.args["parameters"]["test_account"] = "acc-2"
        with self.assertRaisesRegex(mod.CallError, "OpenAPI"):
            adapter.call("objectify_get_account", self.args)
        parameter["schema"] = {"$ref": "https://example.invalid/schema.json"}
        self.assert_config_rejected()
        parameter["schema"] = {"$ref": "#/components/schemas/AccountId", "maxLength": 3}
        self.assert_config_rejected()

    def test_secret_projection_fields_are_rejected(self):
        fields = self.config["operations"]["objectify_get_account"]["response"]["fields"]
        for pointer in ("/secret_key", "/credentials/value", "/nested/accessKey", "/keys/value"):
            with self.subTest(pointer=pointer):
                fields["account_id"]["pointer"] = pointer
                self.assert_config_rejected()

    def test_object_output_cannot_hide_nested_secrets(self):
        self.config["operations"]["objectify_get_account"]["response"]["fields"]["account_id"]["type"] = "object"
        self.assert_config_rejected()

    def test_runtime_object_fails_scalar_projection(self):
        self.record["id"] = {"secret_key": "injected"}
        with self.assertRaises(mod.CallError):
            self.adapter().call("objectify_get_account", self.args)

    def test_auth_token_reflection_is_redacted(self):
        self.record["id"] = os.environ["SDS_OBJECTIFY_TEST_TOKEN"]
        result = self.adapter().call("objectify_get_account", self.args)
        self.assertEqual(result["record"]["account_id"], "[REDACTED]")

    def test_aws_key_pattern_is_redacted(self):
        self.record["id"] = "AKIA0123456789ABCDEF"
        result = self.adapter().call("objectify_get_account", self.args)
        self.assertEqual(result["record"]["account_id"], "[REDACTED]")

    def test_unknown_arguments_urls_and_query_keys_are_refused(self):
        for change in ({"url": "https://evil.invalid"}, {"headers": {"Authorization": "x"}}, {"parameters": {"not_in_schema": "x"}}):
            with self.subTest(change=change):
                args = {**self.args, **change}
                with self.assertRaises(mod.CallError):
                    self.adapter().call("objectify_get_account", args)

    def test_query_injection_and_wrong_types_are_refused(self):
        for value in ("../parlay", "x&customer_id=other", "x\r\nHeader:value", {"x": 1}, 42, True):
            with self.subTest(value=value):
                self.args["parameters"]["test_account"] = value
                with self.assertRaises(mod.CallError):
                    self.adapter().call("objectify_get_account", self.args)

    def test_missing_auth_does_not_send_request(self):
        adapter = self.adapter()
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(mod.CallError):
                adapter.call("objectify_get_account", self.args)
        self.assertEqual(adapter._opener.requests, [])

    def test_request_has_fixed_url_get_method_and_bounded_timeout(self):
        adapter = self.adapter()
        adapter.call("objectify_get_account", self.args)
        request, timeout = adapter._opener.requests[0]
        self.assertEqual(request.full_url, "https://objectify.invalid/api/v1/account/obj_acc?test_account=acc-1")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(timeout, 2)

    def test_redirect_response_is_refused(self):
        response = FakeResponse(self.record, "https://other.invalid/back")
        with self.assertRaisesRegex(mod.CallError, "redirect"):
            self.adapter(response).call("objectify_get_account", self.args)

    def test_html_and_oversized_json_are_refused(self):
        url = "https://objectify.invalid/api/v1/account/obj_acc?test_account=acc-1"
        for response in (FakeResponse(b"<html>secret</html>", url, content_type="text/html"),
                         FakeResponse(b" " * 2048, url)):
            with self.subTest(response=response):
                with self.assertRaises(mod.CallError):
                    self.adapter(response).call("objectify_get_account", self.args)

    def test_upstream_exception_body_and_url_are_not_exposed(self):
        error = urllib.error.HTTPError("https://objectify.invalid?secret=oops", 500, "sensitive-value", {}, io.BytesIO(b"password=sensitive"))
        with self.assertRaises(mod.CallError) as raised:
            self.adapter(error).call("objectify_get_account", self.args)
        self.assertNotIn("sensitive", str(raised.exception))
        self.assertNotIn("oops", str(raised.exception))

    def listing(self):
        operation = copy.deepcopy(self.config["operations"]["objectify_get_account"])
        operation.update({"path": "/getAllSink", "operation_id": "syntheticList", "parameters": {}})
        operation["response"]["records_pointer"] = "/items"
        operation["response"]["many"] = True
        self.config["operations"] = {"objectify_list_accounts": operation}
        self.args["parameters"] = {}

    def test_list_is_blocked_without_listing_scope_review(self):
        self.listing()
        self.assert_config_rejected()

    def test_list_is_blocked_without_both_per_record_scope_checks(self):
        self.listing()
        self.config["contract"]["listing_scope_verified"] = True
        self.config["operations"]["objectify_list_accounts"]["response"]["scope_checks"] = []
        self.assert_config_rejected()

    def test_list_is_bounded_and_checks_even_truncated_records(self):
        self.listing()
        self.config["contract"]["listing_scope_verified"] = True
        records = [copy.deepcopy(self.record) for _ in range(3)]
        result = self.adapter({"items": records}).call("objectify_list_accounts", self.args)
        self.assertEqual(result["returned_count"], 2)
        self.assertTrue(result["locally_truncated"])
        self.assertEqual(result["upstream_completeness"], "unknown")
        records[2]["customer"] = "test-customer-b"
        with self.assertRaises(mod.CallError):
            self.adapter({"items": records}).call("objectify_list_accounts", self.args)

    def test_response_pattern_work_is_preflighted_for_all_received_records(self):
        self.listing()
        self.config["contract"]["listing_scope_verified"] = True
        self.config["limits"].update(max_records=1, max_response_bytes=1024 * 1024)
        response = self.config["operations"]["objectify_list_accounts"]["response"]
        response["fields"] = {
            "label_%02d" % index: {"pointer": "/label", "type": "string", "required": True,
                                  "max_length": 256, "pattern": "[a-z]{1,256}"}
            for index in range(32)
        }
        self.record["label"] = "a" * 256
        records = [copy.deepcopy(self.record) for _ in range(20)]
        adapter = self.adapter({"items": records})
        with mock.patch.object(mod.LinearPattern, "matches", side_effect=AssertionError("Must preflight before matching")):
            with self.assertRaisesRegex(mod.CallError, "Validation work budget exceeded"):
                adapter.call("objectify_list_accounts", self.args)
            # Scope evidence is checked for every record, even past max_records
            # and before the response's accumulated pattern-work rejection.
            records[-1]["customer"] = "test-customer-b"
            with self.assertRaisesRegex(mod.CallError, "outside the configured scope"):
                adapter.call("objectify_list_accounts", self.args)

    def test_tool_result_caps_numeric_projection_amplification(self):
        self.listing()
        self.config["contract"]["listing_scope_verified"] = True
        self.config["limits"].update(max_records=100, max_response_bytes=1024 * 1024)
        response = self.config["operations"]["objectify_list_accounts"]["response"]
        response["fields"] = {
            "counter_%02d" % index: {"pointer": "/usage", "type": "integer", "required": True}
            for index in range(32)
        }
        self.record["usage"] = 10 ** 4000
        payload = {"items": [self.record for _ in range(100)]}
        self.assertLess(len(json.dumps(payload).encode()), self.config["limits"]["max_response_bytes"])
        mcp, _ = self.initialize()
        mcp.adapter._opener = FakeOpener(payload)
        reply = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "objectify_list_accounts", "arguments": self.args}})
        result = reply["result"]
        self.assertTrue(result["isError"])
        self.assertIn("256 KiB", result["content"][0]["text"])
        self.assertNotIn("structuredContent", result)
        self.assertNotIn(str(self.record["usage"]), json.dumps(reply))
        self.assertLess(len(json.dumps(reply).encode()), 1024)
        self.assertEqual(mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "ping"}),
                         {"jsonrpc": "2.0", "id": 3, "result": {}})

    def test_tool_result_cap_counts_unicode_wire_escaping_and_both_forms(self):
        self.listing()
        self.config["contract"]["listing_scope_verified"] = True
        self.config["limits"].update(max_records=6, max_response_bytes=1024 * 1024)
        response = self.config["operations"]["objectify_list_accounts"]["response"]
        response["fields"] = {
            "label_%02d" % index: {"pointer": "/label", "type": "string", "required": True,
                                  "max_length": 256, "pattern": ".*"}
            for index in range(32)
        }
        self.record["label"] = "א" * 256
        payload = {"items": [self.record for _ in range(6)]}
        mcp, _ = self.initialize()
        mcp.adapter._opener = FakeOpener(payload)
        data = mcp.adapter.call("objectify_list_accounts", self.args)
        uncapped = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, allow_nan=False)}],
                    "structuredContent": data, "isError": False}
        self.assertLess(len(json.dumps(uncapped, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
                        mod.MAX_TOOL_RESULT_BYTES)
        self.assertGreater(len(json.dumps(uncapped, ensure_ascii=True, separators=(",", ":")).encode("ascii")),
                           mod.MAX_TOOL_RESULT_BYTES)
        reply = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "objectify_list_accounts", "arguments": self.args}})
        self.assertTrue(reply["result"]["isError"])
        self.assertNotIn("structuredContent", reply["result"])
        # A smaller result succeeds without losing or replacing its fields.
        mcp.adapter.config["limits"]["max_records"] = 1
        reply = mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "objectify_list_accounts", "arguments": self.args}})
        self.assertFalse(reply["result"]["isError"])
        self.assertEqual(reply["result"]["structuredContent"]["returned_count"], 1)
        self.assertEqual(reply["result"]["structuredContent"]["records"][0]["label_00"], self.record["label"])

    def test_upstream_pagination_cannot_be_misreported_as_complete(self):
        self.listing()
        self.config["contract"]["listing_scope_verified"] = True
        for has_more in (True, False):
            result = self.adapter({"items": [self.record], "has_more": has_more, "next": "opaque"}).call("objectify_list_accounts", self.args)
            self.assertFalse(result["locally_truncated"])
            self.assertEqual(result["upstream_completeness"], "unknown")
            self.assertNotIn("truncated", result)
            self.assertNotIn("has_more", result)
            self.assertNotIn("next", result)

    def test_body_deadline_is_enforced_without_waiting(self):
        adapter = self.adapter()
        with mock.patch.object(mod.time, "monotonic", side_effect=[0, 3]):
            with self.assertRaisesRegex(mod.CallError, "body-phase"):
                adapter.call("objectify_get_account", self.args)

    def test_boolean_does_not_pass_integer_output(self):
        self.record["usage"] = True
        with self.assertRaises(mod.CallError):
            self.adapter().call("objectify_get_account", self.args)

    def initialize(self, version="2025-11-25"):
        mcp = mod.MCP(self.adapter())
        response = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": version, "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}})
        mcp.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return mcp, response

    def test_supported_protocols_and_future_counteroffer(self):
        self.assertEqual(mod.PROTOCOLS, ("2025-11-25",))
        for requested in ("2025-11-25", "2025-06-18", "2025-03-26", "2026-07-28"):
            with self.subTest(requested=requested):
                _, response = self.initialize(requested)
                self.assertEqual(response["result"]["protocolVersion"], "2025-11-25")

    def test_modern_probe_gets_method_not_found(self):
        mcp = mod.MCP(self.adapter())
        result = mcp.handle({"jsonrpc": "2.0", "id": 0, "method": "server/discover", "params": {}})
        self.assertEqual(result["error"]["code"], -32601)

    def test_tools_before_initialization_are_refused(self):
        mcp = mod.MCP(self.adapter())
        result = mcp.handle({"jsonrpc": "2.0", "id": 0, "method": "tools/list"})
        self.assertIn("error", result)

    def test_tools_list_accepts_metadata_without_changing_tools(self):
        mcp, _ = self.initialize()
        normal = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        metadata = mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list",
                               "params": {"_meta": {"progressToken": "audit", "com.example/trace": "opaque"}}})
        self.assertEqual(normal["result"], metadata["result"])
        invalid = mcp.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {"_meta": []}})
        self.assertEqual(invalid["error"]["code"], -32602)

    def test_older_request_gets_current_counteroffer_and_structured_content(self):
        mcp, _ = self.initialize("2025-03-26")
        result = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "objectify_status", "arguments": {}}})
        self.assertEqual(mcp.protocol, "2025-11-25")
        self.assertIn("structuredContent", result["result"])

    def test_protocol_validates_ids_and_array_batches(self):
        mcp, _ = self.initialize()
        for request in ([], {"jsonrpc": "2.0", "id": None, "method": "ping"}, {"jsonrpc": "2.0", "id": True, "method": "ping"}):
            self.assertEqual(mcp.handle(request)["error"]["code"], -32600)

    def test_unreadable_error_id_is_omitted_and_readable_id_is_preserved(self):
        mcp, _ = self.initialize()
        self.assertNotIn("id", mcp.error(None, -32700, "Invalid JSON."))
        for request in ([], {"jsonrpc": "2.0", "id": None, "method": "ping"},
                        {"jsonrpc": "2.0", "id": True, "method": "ping"}):
            self.assertNotIn("id", mcp.handle(request))
        for identifier in (0, "audit-id"):
            reply = mcp.handle({"jsonrpc": "2.0", "id": identifier, "method": "unknown/method"})
            self.assertEqual(reply["id"], identifier)
            self.assertEqual(type(reply["id"]), type(identifier))
            malformed = mcp.handle({"jsonrpc": "2.0", "id": identifier, "method": 123})
            self.assertEqual(malformed["id"], identifier)

    def test_duplicate_keys_and_nonfinite_json_are_rejected(self):
        for data in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e9999}'):
            with self.assertRaises(ValueError):
                mod.strict_json(data)

    def test_stdio_rejects_lone_surrogates_then_processes_next_message(self):
        payload = (b'{"jsonrpc":"2.0","id":"\\ud800","method":"ping"}\n'
                   b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n')
        result = subprocess.run([sys.executable, str(SERVER), "--config", str(HERE / "config.example.json")],
                                input=payload, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertNotIn("id", replies[0])
        self.assertEqual(replies[1], {"jsonrpc": "2.0", "id": 2, "result": {}})
        for data in ('{"\\ud800": 1}', '{"value": "\\udfff"}'):
            with self.assertRaises(UnicodeError):
                mod.strict_json(data)
        self.assertEqual(mod.strict_json('"\\ud83d\\ude00"'), "😀")

    def test_deeply_nested_json_is_bounded_and_quoted_braces_are_not_counted(self):
        with self.assertRaises(ValueError):
            mod.strict_json("[" * 10000 + "0" + "]" * 10000)
        value = "[" * 10000 + '\\"' + "}" * 10000
        self.assertEqual(mod.strict_json(json.dumps({"value": value}))["value"], value)

    def test_stdio_survives_deep_invalid_message_and_processes_next_request(self):
        initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}}
        ping = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
        payload = "[" * 10000 + "0" + "]" * 10000 + "\n" + json.dumps(initialize) + "\n" + json.dumps(ping) + "\n"
        result = subprocess.run([sys.executable, str(SERVER), "--config", str(HERE / "config.example.json")],
                                input=payload, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertIn("result", replies[1])
        self.assertEqual(replies[2], {"jsonrpc": "2.0", "id": 2, "result": {}})

    def test_stdio_cli_and_check_are_network_free_with_default(self):
        config = HERE / "config.example.json"
        checked = subprocess.run([sys.executable, str(SERVER), "--config", str(config), "--check"], capture_output=True, text=True, timeout=5)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertFalse(json.loads(checked.stdout)["enabled"])
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "objectify_status", "arguments": {}}},
        ]
        process = subprocess.run([sys.executable, str(SERVER), "--config", str(config)], input="".join(json.dumps(m) + "\n" for m in messages), capture_output=True, text=True, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(result), 3)
        self.assertEqual([t["name"] for t in result[1]["result"]["tools"]], ["objectify_status"])
        self.assertFalse(result[2]["result"]["isError"])

    def test_real_local_redirect_handler_never_follows(self):
        hits = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                self.send_response(302)
                self.send_header("Location", "/must-not-be-requested")
                self.end_headers()
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), mod.NoRedirect())
            try:
                with self.assertRaises(urllib.error.HTTPError):
                    opener.open("http://127.0.0.1:%d/start" % server.server_port, timeout=2)
            except urllib.error.URLError as error:
                # Some sandboxes permit a loopback listener but deny connecting
                # to it. Other transport errors must still fail this test.
                if (isinstance(error.reason, PermissionError)
                        or getattr(error.reason, "winerror", None) == 10013):
                    self.skipTest("Loopback fixture connection is denied by this test environment: " + str(error.reason))
                raise
            self.assertEqual(hits, ["/start"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
