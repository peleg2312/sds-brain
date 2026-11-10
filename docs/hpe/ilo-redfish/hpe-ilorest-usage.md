# Using the RESTful Interface Tool

## Getting started with iLOrest

The first action to perform before being able to use iLOrest is to open a Redfish session in a remote iLO (out-of-band management) or in the local iLO (in-band management). Refer to the generic Redfish authentication methods as well as the login global command for more details.

As mentioned in this blog post, the Redfish® data model is based upon schemas. The HPE iLOrest Redfish client also uses schemas to get or set properties in the Redfish tree. Schemas are referenced as data types, types or selectors in the iLOrest terminology.

To manage a single property, you need first to identify and select its data type (schema file).

The exhaustive list of schemas (selectors) can be retrieved with the types atomic command as shown in the following example.

-

-

-

```
ilorest login <ilo-ip> -u <ilo-user> -p password
ilorest types
ilorest logout
```

If you don't know which schema describes the property you want to manage, follow this method:

- Try to identify a schema name close to the property. If the property belongs to the storage subsystem, look for all selectors having "storage" in their name. Here are a few examples performed against an iLO 6 based system.

Storage: controllers, drives, logical volumes

-

-

```
ilorest login <ilo-ip> -u <ilo-username> -p password
ilorest types | grep -i -E "storage|drive|volume"
ilorest logout
```

Thermal: Fans, temperature

-

-

```
ilorest login <ilo-ip> -u <ilo-username> -p password
ilorest types | grep -i thermal
ilorest logout
```

TIP

For each iLO firmware, you can browse the types from the resource map .

- If the above method fails, enter the property string in the search box of this portal (top right corner). In the proposed list, select a section mentioning "Resource Definition". The type is displayed after string "Member of".

As an example, if you want to view the firmware version of the iLO, type "FirmwareVersion" in the search box and click on "Manager resource definitions > FirmwareVersion". This displays the iLO's FirmwareVersion property, part of the Manager.v schema.

- Select the found schema to manage your property.

-

```
ilorest login <ilo-ip> -u <ilo-user> -p password
ilorest select Manager.

ilorest select
Current selection: Manager.v1_5_1

ilorest get FirmwareVersion
FirmwareVersion=iLO 6 v1.59
```

TIP

iLOrest can select multiple types at once.

The above example appends a . character to the selected type to avoid selecting the other types starting with string Manager like: ManagerCollection, ManagerAccount, etc.

## HPE iLOrest operation modes

HPE iLOrest has three modes of operation. By default, the interactive mode is started when you launch it. With the scriptable mode, you can use a script that calls the program followed by commands and arguments. The file-based mode allows you to use a script that calls the program followed by commands, arguments file(s) to load or save settings.

In addition HPE iLOrest provides a debug mode very helpful for learning and troubleshooting.

### Interactive mode

Interactive mode is started when you run the RESTful Interface Tool without any command-line parameters. An ilorest > prompt is displayed and you can enter commands one at a time. Interactive mode provides immediate feedback for an entered command. You can also use this mode to validate a script.

Use the following instructions to start an interactive session on the different operating systems:

- Microsoft Windows: Go to C:\Program Files\Hewlett Packard Enterprise\RESTful Interface Tool and double-click ilorest.exe. You must be an administrator to run ilorest.exe.

- Linux and Ubuntu: Enter the following command : /usr/sbin/ilorest

- MAC: Enter the following command as administrator: /Applications/ilorest

- VMware ESXi 7.0: Enter the following command as administrator: /opt/tools/ilorest

- VMware ESXi 8.0: Enter the following command as administrator: /opt/ilorest/bin/ilorest.sh

NOTE

In ESXi 7.0/8.0, HPE iLOrest is integrated with the esxcli utility

Here are some Examples:

-

```
esxcli ilorest cmd -q login
esxcli ilorest cmd -q types
esxcli ilorest cmd -q "select Bios."
esxcli ilorest cmd -q logout
esxcli ilorest help
esxcli ilorest debug -q login
esxcli ilorest debug -q logout
```

Use the exit command at the prompt to exit from the interactive mode.

#### Tab command completion

Tab command completion is available for interactive mode in multiple capacities. See the features below.

##### Completing commands

Tab command completion is available for viewing and completing commands.

##### Completing types

Redfish resources and properties are associated to a data type also called resource type or just type. To view or modify a resource, you must first select its type.

TIP

Resource types are listed in the resource map section of the iLO Redfish reference document.

Tab command completion is also available for viewing and completing types.

- You must be logged in a remote or local managed server.

##### Completing properties and sub-properties

Tab command completion is also available for viewing and completing properties.

- You must be logged in and have a type selected.

- Also available for set and list commands.

##### Completing schema properties information

Tab command completion can also show schema information for properties.

- You must be logged in and have a type selected

- Also available for set and list

### Scriptable mode

You can use the scriptable mode to script all the commands using an external input file. The script contains a list of HPE iLOrest command lines that let users get and set properties of server objects.

The following example retrieves information regarding the Bios type:

-

-

```
:: This is a batch file that logs into a remote server,
:: selects the Bios type, and gets the BootMode value

:: Usage ::
:: selectget.bat [URI] [USERNAME] [PASSWORD]
@echo off

set argC=0
for %%x in (%*) do Set /A argC+=1
if %argC% LSS 3 goto :failCondition
goto :main

:failCondition
@echo Usage:
@echo selectget.bat [URI] [USERNAME] [PASSWORD]
goto :EOF

:main
@echo *****************************************
@echo ************* Logging in... *************
@echo *****************************************
ilorest.exe login %1 -u %2 -p %3
@echo *****************************************
@echo ******* selecting Bios type... ********
@echo *****************************************
ilorest.exe select Bios.
@echo *****************************************
@echo ********** getting BootMode... **********
@echo *****************************************
ilorest.exe get BootMode
pause
```

### File-based mode

File-based mode allows you to save and load settings from a file. This is similar to the conrep.dat files used by CONREP. File-based mode supports the JSON format.

The following script allows you to save, edit, and load a file to the server.

The resources and properties of the Bios type is saved to a file called ilorest1.json. Then, after you modify any properties, the load command is used to make these changes on the server. Changes to read-only values are not reflected.

-

-

```
:: This is a file-based edit mode helper for RESTful Interface Tool
:: 1. Run to download selected type to a file called ilorest.json
:: 2. Edit the ilorest.json file to make changes.
:: 3. Press any key running batch program to continue with program,
::    uploading the newly edited program to the server.

:: Usage ::
:: saveload.bat [SELECTOR] [FILENAME]
:: Specify a type with the SELECTOR tag, and
:: save to a file called FILENAME
@echo off
set argC=0
for %%x in (%*) do Set /A argC+=1
if %argC% LSS 2 goto :failCondition
goto :main

:failCondition
@echo Usage:
@echo saveload.bat [SELECTOR] [FILENAME]
@echo specify a type with the SELECTOR tag, and
@echo save to a file called FILENAME
goto :EOF

:main
ilorest.exe login
ilorest.exe save --selector=%1 --json -f %2
@echo Edit the file, then:
pause
ilorest.exe load -f %2
```

When the example script is run, the following output is produced:

## Atomic, macro commands and raw commands

HPE iLOrest provides three types of commands:

- Atomic commands also referred as global commands. The most common are select, get, set and commit. They are mostly used to manage individual properties or resources.

- Macro commands used to manage groups of resources or perform complex actions involving several properties. BIOS, iLO, and Storage controller commands are just a few examples.

- Raw commands: They are the equivalent of HTTP PATCH, GET, POST, PUT, DELETE, and HEAD requests.

## Executing commands in parallel

HPE iLOrest uses a caching method to locally save servers' data. To send HPE iLOrest commands to many different remotely systems at once, you need to specify a different cache directory for each of them. The following example uses clush, the ClusterShell, but any method of parallel scripting will work as long as you specify different cache directories.

The following example executes clush commands to start HPE iLOrest sessions against ten different iLO based servers. Each session is composed of the login, a chassis serial number retrieval and the logout.

For each session, HPE iLOrest saves cached data in a different location: server1 data is cached in directory ilo-server1, server2 data is cached in directory ilo-server2....

The --nostdin parameter tells clush not to wait for standard inputs. The --worker=exec parameter executes the HPE iLOrest local executable. The -w server[1-10] part of the example replaces the string %h in the rest of the command with 1, 2, ..., 10.

-

-

```
clush --nostdin --worker=exec -w 'server[1-10]' ilorest --cache-dir=ilo-%h login ilo-%h -u ilo-user -p password
clush --nostdin --worker=exec -w 'server[1-10]' ilorest --cache-dir=ilo-%h get --json SerialNumber --selector Chassis.
clush --nostdin --worker=exec -w 'server[1-10]' ilorest --cache-dir=ilo-%h logout
```

Running HPE iLOrest against multiple managed systems can also be done using automation tools such as Ansible, Chef, and Puppet.

## Concurrent in-band execution on a single server

The previous section describes running iLOrest against many different servers at once (out-of-band). This section covers a different scenario: running several iLOrest sessions concurrently against the same server in local / in-band mode. The behavior and limits differ by iLO generation, because the underlying in-band transport is different.

### Terminology used in this section

To avoid ambiguity, the rest of this section uses these terms precisely:

- Session — a logical connection to iLO, opened by ilorest login and closed by ilorest logout. The session token is stored in a cache directory and is reused by every command that points at the same cache directory. A single iLO supports up to 8 concurrent in-band sessions. In this section, each parallel unit of work runs exactly one session end to end — a login, one or more commands, and a logout, all pointing at the same cache directory (or all using --nocache). Running these sessions in parallel opens multiple concurrent in-band sessions.

Because each session is opened and closed as one self-contained unit, the number of concurrent sessions is what you cap to stay within the 8-session in-band limit.

MANDATORY: isolate the cache for every concurrent session

When running parallel iLOrest sessions in-band against the same iLO, you must do one of the following for every session — without exception:

- Pass a unique --cache-dir <path> to every iLOrest session creation of that session (login, each command, and logout must all use the same unique path), or

- Pass --nocache to every iLOrest session creation so that iLOrest creates a fresh temporary session without touching the cache at all.

Concurrent sessions that share the default cache (~/.ilorest / /root/.ilorest) overwrite each other's session token. A logout (or crash) in one session then invalidates every other active session. This is the most common cause of intermittent Error accessing the file path... failures (return code 7) under concurrency. There is no safe way to run parallel in-band iLOrest sessions without --cache-dir or --nocache.

Tip

Always issue a formal logout as soon as a session is done. Closing sessions promptly frees in-band slots and helps you stay under the limit of 8 concurrent in-band sessions.

Credential handling

The example scripts in this section show USER="admin" / PASS="password" inline only to keep the examples self-contained. Never hardcode iLO credentials in plaintext in production scripts. Supply them instead from an environment variable, a secret manager, or the iLOrest configuration file (redfish.conf), and restrict access to any file that stores them.

The table below summarizes the in-band behavior of each iLO generation. The sections that follow describe each generation in detail.

### Behavior by iLO generation

iLO generation | Default in-band path | Concurrent in-band limit | Per-session --cache-dir or --nocache | Credentials required in-band

iLO 7 and later | vNIC + application account (TPM-backed), serialized across sessions | 8 concurrent sessions | Mandatory — a unique --cache-dir per session, or --nocache on every ilorest session creation | Default login uses the application account (no credentials); required for non-privileged users in SecureStandard state, and for all users in higher security states

iLO 5 / iLO 6 | CHIF driver + blobstore | 8 concurrent sessions | Mandatory — a unique --cache-dir per session, or --nocache on every ilorest session creation | For non-privileged users in Production state and for all users in higher security state.

#### iLO 7 and later

The default in-band communication path of iLO 7 based servers and later is the Virtual NIC (vNIC), and the default login authenticates with an application account token that is protected by the server's TPM. Because the TPM is a single shared resource, iLOrest serializes TPM access across sessions: concurrent sessions that perform an app-account login, rawget, or logout take turns on the TPM rather than failing. The 8-session in-band guidance still applies.

- Mandatory: give each session a unique --cache-dir <path>, or pass --nocache to every ilorest session creation — the same mandatory cache-isolation rule as for iLO 5 / iLO 6. On iLO 7 the TPM serialization adds queuing delays between sessions; a missing or shared cache directory turns those delays into session corruption.

- Because TPM access is serialized, the login phase of concurrent sessions runs effectively one at a time. When running many sessions, allow a generous per-session timeout so that sessions waiting for the TPM lock are not killed prematurely.

- To bypass the application account and log in with iLO credentials over vNIC instead, add --no_app_account together with -u <user> -p <password>.

NOTE

HPE iLOs in SecureStandard, FIPS or CNSA security states have additional restrictions on in-band access. Refer to this section for more information.

#### iLO 5 and iLO 6

In-band communication with iLO 5 and iLO 6 based servers goes through the CHIF driver and the blobstore. Up to 8 concurrent in-band sessions are supported simultaneously, as documented for the HPE Python Redfish library that iLOrest is built on.

- Start no more than 8 concurrent in-band sessions at a time.

- Mandatory: give each session a unique --cache-dir <path>, or pass --nocache to every ilorest session creation. Omitting both causes concurrent sessions to corrupt each other's session token in the shared default cache.

- Privileged local users (root / Administrator) do not need to pass iLO credentials for in-band CHIF access in Production security state. Non-privileged users in Production, and all users in higher security states, must elevate privilege (sudo / Administrator) and pass iLO credentials with the command.

- CHIF is the default in-band path on these generations. To force an in-band login over the Virtual NIC instead, use --force_vnic.

NOTE

HPE iLOs in HighSecurity, FIPS or CNSA security states have additional restrictions on in-band access. Refer to this section for more information.

### Example: concurrent in-band sessions on one server

This is deliberately a minimal, cross-generation example: it introduces the single safety pattern that every iLO generation shares — a private cache directory per session (or --nocache) plus a self-contained login → rawget → logout in each session. The generation-specific, production-ready scripts that follow build on it: Production bash script and Using --nocache cover the iLO 7 application-account / Virtual NIC path, while Parallel in-band CHIF execution (iLO 5 / iLO 6) covers the different iLO 5 / iLO 6 transport (the CHIF driver + blobstore), which requires credential-based login -u -p for non-privileged users and enforces the hard 8-session blobstore limit. That is why the two paragraphs coexist: this one is the shared introductory pattern, and the CHIF paragraph is the iLO 5 / iLO 6 production counterpart to the iLO 7 scripts.

#### Minimal example: isolated cache directory per session

Each session runs one session end to end and uses its own cache directory — this is mandatory for correct operation. Without it, a logout in one session immediately invalidates every other running session. Each session performs a login, a rawget, and a logout, so no session can clobber another running session. It works on iLO 5, iLO 6, and iLO 7 based servers. On iLO 7 the default login (no URL, no credentials) uses the application account; to log in with iLO credentials instead, add --no_app_account -u <user> -p <password> (the --no_app_account flag is an iLO 7 and later option). On iLO 5 and iLO 6, pass -u <user> -p <password> to log in with credentials.

This example uses the --cache-dir approach, which keeps one private session cache per session. The mutually exclusive --nocache approach — where ilorest opens a fresh session without any cache directory — is shown in Using --nocache instead of isolated cache directories further down. Use one approach or the other, never both on the same command line.

The examples do not pass --nostdout. That flag only has an effect when debug logging is enabled (-d / --debug), where it keeps the debug output off standard output. Because these examples do not enable debug, --nostdout would do nothing and is omitted. If you turn on debug logging, add --nostdout alongside -d to stop the debug stream from cluttering the terminal; it never affects data saved with -f.

-

-

```
run_ilorest_session() {
    id="$1"
    cachedir=$(mktemp -d "/tmp/ilorest_cache_${id}_XXXX")
    tmpfile=$(mktemp "/tmp/ilorest_${id}_XXXX.json")
    trap "rm -rf '$cachedir' '$tmpfile'" RETURN

    # On iLO 7, login uses the application account by default. To use iLO
    # credentials instead, add: --no_app_account -u "$USER" -p "$PASS"
    # On iLO 5 / iLO 6, pass just -u "$USER" -p "$PASS" to log in.
    ilorest --cache-dir "$cachedir" login || return 1

    ilorest --cache-dir "$cachedir" rawget \
        "/redfish/v1/Systems/1/Storage/?\$expand=." -f "$tmpfile" || {
        ilorest --cache-dir "$cachedir" logout
        return 1
    }

    ilorest --cache-dir "$cachedir" logout
}
export -f run_ilorest_session

# Run 5 sessions, 3 at a time.
seq 1 5 | xargs -I{} -P3 bash -c 'run_ilorest_session "{}"'
```

NOTE

Keep the number of simultaneous in-band sessions at 8 or fewer. On iLO 7, because TPM access is serialized, set any per-session timeout comfortably above (number of concurrent sessions) x (single login time) so that sessions queued on the TPM lock are not timed out.

#### Production bash script: app-account login with isolated cache directories

The minimal example above illustrates the essential pattern. The following production-ready script extends it with per-session timeouts, a shared log file, a summary file, and final statistics. It targets iLO 7 and later, where the default login (no URL, no credentials) authenticates using the server's application account token over the Virtual NIC.

NOTE

The three production-ready scripts that follow (app-account, --nocache, and CHIF) are written for Linux / bash. The safety rules they demonstrate — a unique --cache-dir per session or --nocache, prompt logout, per-session timeouts, and the 8-session limit — apply identically on Windows. To reproduce them on Windows, adapt the Windows / batch minimal example above (or a PowerShell equivalent that launches sessions in the background), keeping the same per-session cache isolation and cleanup.

Every concurrent session must receive its own --cache-dir — omitting it means concurrent sessions share the default cache and will destroy each other's session tokens. The trap … EXIT in each session cleans up the temporary directory automatically so no stale cache files accumulate under /tmp.

```
#!/usr/bin/env bash
# Runs TOTAL_RUNS iLOrest sessions, CONCURRENT_SESSIONS at a time.
# Each session gets a private --cache-dir so concurrent sessions cannot clobber
# each other's session token in the shared default cache (~/.ilorest).
#
# iLO 7+: login with no URL and no credentials uses the application account
# over the Virtual NIC (the default in-band path).
set -u

CONCURRENT_SESSIONS=8   # parallel ilorest sessions
TOTAL_RUNS=5         # total number of sessions to run
TIMEOUT=60           # per-session timeout in seconds

LOG_FILE="parallel_ilorest_test.log"
SUMMARY_FILE="parallel_summary.log"

: > "$LOG_FILE"
: > "$SUMMARY_FILE"

run_session() {
    local id="$1"
    local cachedir tmpfile status start_ts end_ts duration

    start_ts=$(date +%s.%N)
    status="SUCCESS"

    tmpfile=$(mktemp "/tmp/ilorest_${id}_XXXX.json")
    # Private session cache directory for this session — created fresh every run.
    cachedir=$(mktemp -d "/tmp/ilorest_cache_${id}_XXXX")
    trap "rm -rf '$tmpfile' '$cachedir'" EXIT

    {
        echo "[INFO] Session $id started (cache-dir=$cachedir)"

        # Pass --cache-dir to every ilorest call in this session so they all share
        # the same private session token (login, rawget, and logout must match).
        ilorest --cache-dir "$cachedir" login || {
            echo "[ERROR] Session $id: login failed"
            status="FAIL_LOGIN"; exit 1
        }

        ilorest --cache-dir "$cachedir" \
            rawget "/redfish/v1/Systems/1/Storage/?\$expand=." \
            -f "$tmpfile" || {
            echo "[ERROR] Session $id: rawget failed"
            status="FAIL_RAWGET"
            ilorest --cache-dir "$cachedir" logout
            exit 1
        }

        ilorest --cache-dir "$cachedir" logout || \
            echo "[WARN] Session $id: logout failed"

        echo "[INFO] Session $id completed"
    } >> "$LOG_FILE" 2>&1

    end_ts=$(date +%s.%N)
    duration=$(awk "BEGIN {print $end_ts - $start_ts}")
    echo "SESSION=$id STATUS=$status DURATION=${duration}s" >> "$SUMMARY_FILE"
}
export -f run_session
export LOG_FILE SUMMARY_FILE

echo "[INFO] Starting: $TOTAL_RUNS sessions / $CONCURRENT_SESSIONS concurrent" | tee -a "$LOG_FILE"

seq "$TOTAL_RUNS" | xargs -I{} -P "$CONCURRENT_SESSIONS" bash -c '
    id="$1"
    timeout '"$TIMEOUT"'s bash -c "run_session $id" \
        || echo "SESSION=$id STATUS=TIMEOUT DURATION='"$TIMEOUT"'s" >> "'"$SUMMARY_FILE"'"
' _ {}

echo "========== SUMMARY =========="
awk '/STATUS=SUCCESS/{s++} /FAIL_/{f++} /STATUS=TIMEOUT/{t++} {n++}
     END{print "Total:",n,"  Success:",s+0,"  Failures:",f+0,"  Timeouts:",t+0}' \
    "$SUMMARY_FILE"
```

Key points:

- --cache-dir "$cachedir" is mandatory for every ilorest session creation within a session (login, rawget, logout). All three calls must reference the same private directory so they share one session token. Omitting --cache-dir (or reusing the same directory across sessions) causes one session's logout to invalidate another session's active session.

- mktemp -d creates a unique temporary directory per session. The trap … EXIT removes it automatically when the session exits, preventing stale cache accumulation under /tmp.

- timeout ${TIMEOUT}s prevents a hung session from blocking the pipeline indefinitely.

- On iLO 7, TPM access is serialized across sessions (the TPM named semaphore allows only one holder at a time). Set TIMEOUT well above CONCURRENT_SESSIONS × (single login time) so that sessions waiting on the TPM lock are not killed prematurely.

Expected output

On success, each session writes its Redfish payload to its own -f file and the script prints a summary. A healthy run of 5 sessions looks like this:

```
[INFO] Starting: 5 sessions / 8 concurrent
========== SUMMARY ==========
Total: 5   Success: 5   Failures: 0   Timeouts: 0
```

The per-session $LOG_FILE (parallel_ilorest_test.log) records the lifecycle of each session, and $SUMMARY_FILE (parallel_summary.log) has one line per session:

```
SESSION=1 STATUS=SUCCESS DURATION=3.42s
SESSION=2 STATUS=SUCCESS DURATION=3.51s
...
```

If a session fails, its summary line shows the failing phase — STATUS=FAIL_LOGIN, STATUS=FAIL_RAWGET, or STATUS=TIMEOUT — and the log file contains the matching [ERROR] line. A shared-cache collision typically surfaces as an Error accessing the file path... (return code 7) in the log, which is exactly what the per-session --cache-dir prevents.

#### Using --nocache instead of isolated cache directories

The --nocache global flag tells iLOrest to skip the data and session cache entirely. Instead of restoring a previously cached session, ilorest creates a fresh temporary session directly against iLO. It is the alternative to --cache-dir for making parallel in-band sessions safe: use one or the other — never both.

Mutually exclusive

--cache-dir and --nocache are mutually exclusive; never pass them on the same command line. --cache-dir gives a session its own private cache directory, whereas --nocache disables the cache altogether. Choose the approach that matches your scenario:

Option | Effect | Use when

--cache-dir <unique-path> | Each session reads/writes its own isolated cache directory | You want session reuse within a multi-step session (login → commands → logout)

--nocache | iLOrest ignores the cache entirely; and creates a fresh session. | You want a guaranteed fresh session on each call, or you are testing the direct-to-iLO path

When to use --nocache

Use --nocache when:

- You need a guaranteed fresh iLO session for every operation (no cached credential reuse).

- You are testing the direct-to-iLO in-band path, not the session-restore path.

- You want to exercise the TPM named-semaphore serialization (TpmFileLock) that iLOrest uses to serialize concurrent in-band / application-account operations on iLO 7.

Avoid --nocache in scripts that call ilorest many times against the same server in a loop, because every call incurs a full login / logout round-trip.

On iLO 7 with concurrent sessions, --nocache routes every call through the application-account / Virtual NIC path and exercises the TPM file-lock that serializes TPM semaphore access across sessions. 8 concurrent sessions remains the hard in-band ceiling, but because every --nocache session performs a full TPM-backed login round-trip that queues on the TPM lock, a lower concurrency (for example 4) usually gives better throughput and fewer timeouts than the cached variant. Expect longer per-session times and set timeouts accordingly.

```
#!/usr/bin/env bash
# Same concurrency scenario as the previous script, but every ilorest
# session creation uses --nocache instead of a per-session --cache-dir (the two are
# mutually exclusive). --nocache skips the session cache and creates a fresh
# temporary session directly against iLO.
set -u

CONCURRENT_SESSIONS=4   # 8 is the hard in-band ceiling; use fewer here because each
                     # session does a full login round-trip that contends on the TPM lock
TOTAL_RUNS=5
TIMEOUT=60

LOG_FILE="parallel_ilorest_nocache_test.log"
SUMMARY_FILE="parallel_nocache_summary.log"

: > "$LOG_FILE"
: > "$SUMMARY_FILE"

run_session() {
    local id="$1"
    local tmpfile status start_ts end_ts duration

    start_ts=$(date +%s.%N)
    status="SUCCESS"

    tmpfile=$(mktemp "/tmp/ilorest_${id}_XXXX.json")
    trap "rm -f '$tmpfile'" EXIT

    {
        echo "[INFO] Session $id started (--nocache)"

        # --nocache: bypass the session cache; creates a fresh direct-to-iLO
        # ilorest session. Do not combine it with --cache-dir.
        ilorest --nocache login || {
            echo "[ERROR] Session $id: login failed"
            status="FAIL_LOGIN"; exit 1
        }

        ilorest --nocache \
            rawget "/redfish/v1/Systems/1/Storage/?\$expand=." \
            -f "$tmpfile" || {
            echo "[ERROR] Session $id: rawget failed"
            status="FAIL_RAWGET"
            ilorest --nocache logout
            exit 1
        }

        ilorest --nocache logout || \
            echo "[WARN] Session $id: logout failed"

        echo "[INFO] Session $id completed"
    } >> "$LOG_FILE" 2>&1

    end_ts=$(date +%s.%N)
    duration=$(awk "BEGIN {print $end_ts - $start_ts}")
    echo "SESSION=$id STATUS=$status DURATION=${duration}s" >> "$SUMMARY_FILE"
}
export -f run_session
export LOG_FILE SUMMARY_FILE

echo "[INFO] Starting (--nocache): $TOTAL_RUNS sessions / $CONCURRENT_SESSIONS concurrent" | tee -a "$LOG_FILE"

seq "$TOTAL_RUNS" | xargs -I{} -P "$CONCURRENT_SESSIONS" bash -c '
    id="$1"
    timeout '"$TIMEOUT"'s bash -c "run_session $id" \
        || echo "SESSION=$id STATUS=TIMEOUT DURATION='"$TIMEOUT"'s" >> "'"$SUMMARY_FILE"'"
' _ {}

echo "========== SUMMARY (--nocache) =========="
awk '/STATUS=SUCCESS/{s++} /FAIL_/{f++} /STATUS=TIMEOUT/{t++} {n++}
     END{print "Total:",n,"  Success:",s+0,"  Failures:",f+0,"  Timeouts:",t+0}' \
    "$SUMMARY_FILE"
```

Key differences from the cached variant:

- --nocache is added to every ilorest session creation — login, rawget, and logout.

- CONCURRENT_SESSIONS=4 — 8 remains the hard in-band ceiling, but each session contends on the TPM lock for a full login round-trip, so a lower concurrency reduces queuing and timeout failures on the --nocache path.

- --nocache replaces --cache-dir — the two are mutually exclusive, so this variant passes only --nocache and creates no per-session cache directory.

#### iLO 7 credential login with --no_app_account

The examples above use the iLO 7 default login (no URL, no credentials), which authenticates with the TPM-backed application account. To log in with iLO credentials over the Virtual NIC instead — bypassing the application account — add the --no_app_account flag together with -u <user> -p <password>. This is useful when the application account is disabled or when you must authenticate as a specific iLO user. The same mandatory cache-isolation rule still applies: use a unique --cache-dir per session (shown here) or --nocache.

```
#!/usr/bin/env bash
# iLO 7+ in-band over vNIC, authenticating with iLO credentials instead of the
# application account (--no_app_account). Each session gets its own --cache-dir.
set -u

USER="admin"
PASS="password"
CONCURRENT_SESSIONS=8   # same 8-session in-band limit
TOTAL_RUNS=8
TIMEOUT=120

LOG_FILE="noappaccount_parallel_test.log"
SUMMARY_FILE="noappaccount_parallel_summary.log"

: > "$LOG_FILE"
: > "$SUMMARY_FILE"

run_session() {
    local id="$1"
    local cachedir tmpfile status start_ts end_ts duration

    start_ts=$(date +%s.%N)
    status="SUCCESS"

    tmpfile=$(mktemp "/tmp/ilorest_${id}_XXXX.json")
    cachedir=$(mktemp -d "/tmp/ilorest_cache_${id}_XXXX")
    trap "rm -rf '$tmpfile' '$cachedir'" EXIT

    {
        echo "[INFO] Session $id started (cache-dir=$cachedir)"

        # --no_app_account: log in with iLO credentials over vNIC instead of the
        # application account. iLO 7 and later only.
        ilorest --cache-dir "$cachedir" \
            login --no_app_account -u "$USER" -p "$PASS" || {
            echo "[ERROR] Session $id: login failed"
            status="FAIL_LOGIN"; exit 1
        }

        ilorest --cache-dir "$cachedir" \
            rawget "/redfish/v1/Systems/1/Storage/?\$expand=." \
            -f "$tmpfile" || {
            echo "[ERROR] Session $id: rawget failed"
            status="FAIL_RAWGET"
            ilorest --cache-dir "$cachedir" logout
            exit 1
        }

        ilorest --cache-dir "$cachedir" logout || \
            echo "[WARN] Session $id: logout failed"

        echo "[INFO] Session $id completed"
    } >> "$LOG_FILE" 2>&1

    end_ts=$(date +%s.%N)
    duration=$(awk "BEGIN {print $end_ts - $start_ts}")
    echo "SESSION=$id STATUS=$status DURATION=${duration}s" >> "$SUMMARY_FILE"
}
export -f run_session
export USER PASS LOG_FILE SUMMARY_FILE

echo "[INFO] Starting --no_app_account parallel sessions: $TOTAL_RUNS / $CONCURRENT_SESSIONS concurrent" | tee -a "$LOG_FILE"

seq "$TOTAL_RUNS" | xargs -I{} -P "$CONCURRENT_SESSIONS" bash -c '
    id="$1"
    timeout '"$TIMEOUT"'s bash -c "run_session $id" \
        || echo "SESSION=$id STATUS=TIMEOUT DURATION='"$TIMEOUT"'s" >> "'"$SUMMARY_FILE"'"
' _ {}

echo "========== SUMMARY (--no_app_account) =========="
awk '/STATUS=SUCCESS/{s++} /FAIL_/{f++} /STATUS=TIMEOUT/{t++} {n++}
     END{print "Total:",n,"  Success:",s+0,"  Failures:",f+0,"  Timeouts:",t+0}' \
    "$SUMMARY_FILE"
```

NOTE

To switch the --cache-dir variant above to the --nocache approach, replace every --cache-dir "$cachedir" with --nocache (and drop the cachedir creation and cleanup) — the two are mutually exclusive.

#### Parallel in-band CHIF execution (iLO 5 / iLO 6)

On iLO 5 and iLO 6, in-band communication uses the CHIF driver and the blobstore rather than the Virtual NIC. The same mandatory rule applies: every concurrent session must use either a unique --cache-dir <path> or --nocache on every ilorest session creation.

```
#!/usr/bin/env bash
# iLO 5 / iLO 6 in-band: CHIF driver + blobstore, up to 8 parallel sessions.
# Adjust USER, PASS, and CONCURRENT_SESSIONS (max 8) as needed.
set -u

USER="admin"
PASS="password"
CONCURRENT_SESSIONS=8   # hard limit for CHIF in-band parallel sessions
TOTAL_RUNS=8
TIMEOUT=120

LOG_FILE="chif_parallel_test.log"
SUMMARY_FILE="chif_parallel_summary.log"

: > "$LOG_FILE"
: > "$SUMMARY_FILE"

run_chif_session() {
    local id="$1"
    local cachedir tmpfile status start_ts end_ts duration

    start_ts=$(date +%s.%N)
    status="SUCCESS"

    tmpfile=$(mktemp "/tmp/ilorest_chif_${id}_XXXX.json")
    cachedir=$(mktemp -d "/tmp/ilorest_cache_chif_${id}_XXXX")
    trap "rm -rf '$tmpfile' '$cachedir'" EXIT

    {
        echo "[INFO] CHIF Session $id started (cache-dir=$cachedir)"

        # Privileged local users (root/Administrator) do NOT need credentials for
        # in-band CHIF access in Production security state. Non-privileged users,
        # and all users in higher security states, must pass iLO credentials, as
        # shown here.
        ilorest --cache-dir "$cachedir" \
            login -u "$USER" -p "$PASS" || {
            echo "[ERROR] CHIF Session $id: login failed"
            status="FAIL_LOGIN"; exit 1
        }

        ilorest --cache-dir "$cachedir" \
            rawget "/redfish/v1/Systems/1/" -f "$tmpfile" || {
            echo "[ERROR] CHIF Session $id: rawget failed"
            status="FAIL_RAWGET"
            ilorest --cache-dir "$cachedir" logout
            exit 1
        }

        ilorest --cache-dir "$cachedir" logout || \
            echo "[WARN] CHIF Session $id: logout failed"

        echo "[INFO] CHIF Session $id completed"
    } >> "$LOG_FILE" 2>&1

    end_ts=$(date +%s.%N)
    duration=$(awk "BEGIN {print $end_ts - $start_ts}")
    echo "SESSION=$id STATUS=$status DURATION=${duration}s" >> "$SUMMARY_FILE"
}
export -f run_chif_session
export USER PASS LOG_FILE SUMMARY_FILE

echo "[INFO] Starting CHIF parallel sessions: $TOTAL_RUNS / $CONCURRENT_SESSIONS concurrent" | tee -a "$LOG_FILE"

seq "$TOTAL_RUNS" | xargs -I{} -P "$CONCURRENT_SESSIONS" bash -c '
    id="$1"
    timeout '"$TIMEOUT"'s bash -c "run_chif_session $id" \
        || echo "SESSION=$id STATUS=TIMEOUT DURATION='"$TIMEOUT"'s" >> "'"$SUMMARY_FILE"'"
' _ {}

echo "========== SUMMARY (CHIF) =========="
awk '/STATUS=SUCCESS/{s++} /FAIL_/{f++} /STATUS=TIMEOUT/{t++} {n++}
     END{print "Total:",n,"  Success:",s+0,"  Failures:",f+0,"  Timeouts:",t+0}' \
    "$SUMMARY_FILE"
```

CHIF parallel limit

Do not exceed 8 simultaneous in-band CHIF sessions on a single iLO 5 or iLO 6 based server. Exceeding this limit causes connection failures in the blobstore layer. See the HPE Python Redfish library parallel in-band guidance for background.

The example above uses --cache-dir. To use the mutually exclusive --nocache approach instead — a fresh direct-to-iLO CHIF session on every call, with no per-session cache directory — replace the login/rawget/logout block accordingly:

```
run_chif_session() {
    local id="$1"
    local tmpfile status start_ts end_ts duration

    start_ts=$(date +%s.%N)
    status="SUCCESS"

    tmpfile=$(mktemp "/tmp/ilorest_chif_${id}_XXXX.json")
    trap "rm -f '$tmpfile'" EXIT

    {
        echo "[INFO] CHIF Session $id started (--nocache)"

        # --nocache: bypass the session cache; creates a fresh direct-to-iLO CHIF
        # session. Do not combine it with --cache-dir. Privileged local users in
        # Production state may omit -u/-p; other users must pass credentials.
        ilorest --nocache login -u "$USER" -p "$PASS" || {
            echo "[ERROR] CHIF Session $id: login failed"
            status="FAIL_LOGIN"; exit 1
        }

        ilorest --nocache rawget "/redfish/v1/Systems/1/" -f "$tmpfile" || {
            echo "[ERROR] CHIF Session $id: rawget failed"
            status="FAIL_RAWGET"
            ilorest --nocache logout
            exit 1
        }

        ilorest --nocache logout || \
            echo "[WARN] CHIF Session $id: logout failed"

        echo "[INFO] CHIF Session $id completed"
    } >> "$LOG_FILE" 2>&1

    end_ts=$(date +%s.%N)
    duration=$(awk "BEGIN {print $end_ts - $start_ts}")
    echo "SESSION=$id STATUS=$status DURATION=${duration}s" >> "$SUMMARY_FILE"
}
```

The rest of the script (variables, export, and the xargs launcher) is unchanged from the --cache-dir variant above.

## Configuration file

The HPE iLOrest configuration file (redfish.conf) contains the default settings for the tool. You can use a text editor to change the behavior of the tool such as adding a server IP address, username, and password. The settings that you add or update in the configuration file are automatically loaded each time you start the tool.

Configuration file locations (only present for Windows/Linux/Ubuntu OS):

- Windows OS: The same location as the ilorest.exe executable.

- Linux/Ubuntu OS: /etc/ilorest/redfish.conf

-

-

```
[ilorest]
#iLOrest reads the following environment variables, and applies them at runtime.
#Note that they can be overridden by command line switches.

#####          Log Settings          #####
##########################################
# directory where iLOrest writes its log file
# logdir = .\ilorest_logs

#####         Cache Settings         #####
##########################################
# option to disable caching of all data
# cache = False

#####       Credential Settings      #####
##########################################
# option to use the provided url to login
# url = https://127.0.0.1

# option to use the provided username to login
# username = admin

# option to use the provided password to login
# password = password

# option to use the provided TLS certificate or certificate bundle for HTTPS validation
#tlscert = .\

#####         Commit Settings        #####
##########################################
# flag to commit in all places where applicable
# commit = True

#####    Output Default Settings     #####
##########################################
# flag to change output format in all places where applicable
# format = json

#####    Schema Default Settings     #####
##########################################
# directory where iLOrest will look for ilo schemas
# iloschemadir = .\

# directory where iLOrest will look for bios schemas
# biosschemadir = .\

#####  Default Save/Load Settings    #####
##########################################
# option to set default save output file
# savefile = ilorest.json

# option to set default load input file
# loadfile = ilorest.json
```
