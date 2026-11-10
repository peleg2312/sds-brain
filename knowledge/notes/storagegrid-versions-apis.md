# StorageGRID: versions and the three APIs

## Versions
The fleet runs 11.8, 11.9 and 12. The library holds the full manuals of 11.8, 11.9 and 12.0 as products
`storagegrid-118`, `storagegrid-119`, `storagegrid-120`: always search the installed one. The exact minor / build /
hotfix of each grid belongs in `environment.md`; until the "12" grids are confirmed, say that 12.0 pages are assumed.
For every incident note the grid, release / build, site scope, observed time and the documentation version used.

## Three interfaces
| Interface | Purpose | Identity |
|---|---|---|
| S3 data API | Object and bucket requests from applications | Access keys and S3 policies |
| Grid Management API | Grid-wide administration and inventory | Grid Manager account and group permissions |
| Tenant Management API | Management inside one tenant | Tenant identity and tenant permissions |

- StorageGRID documents `/grid`, `/org` and `/private` resource families. Private endpoints can change without
  notice and ignore the API version: never build a private API call from an old incident. Use the installed grid's
  Swagger page and approved read operations (admin/using-grid-management-api).
- Tenant API authentication (bearer token, with an SSO caveat) is separate from S3 access keys
  (tenant/understanding-tenant-management-api).

## Objectify mapping
An Objectify account is a **StorageGRID tenant** here (an RGW user on Ceph). A tenant has its own users, groups,
buckets and objects: it is not one S3 key or one tenant user. Keep the Objectify account ID, backend kind, grid,
tenant ID and principal as separate fields.

## Release notes
The public release-notes pages of 11.9 and 12.0 link to a support-login PDF for fixed and known issues. Those PDFs are
not in the library: ask the user for the release notes of the exact build before judging a defect or an upgrade
path (or add them under `docs/netapp/`).
