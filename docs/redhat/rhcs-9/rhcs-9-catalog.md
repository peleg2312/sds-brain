# Red Hat Ceph Storage 9 documentation catalog

This page is a catalog of the Red Hat Ceph Storage (RHCS) 9 publications, not the manuals themselves: it says which
guide answers what and where to get it. Cite the guide's own URL, not this page, and say when the guide's text was not
in the library. Landing page: https://docs.redhat.com/en/documentation/red_hat_ceph_storage/9 (catalogued 2026-11-11).

## Format and versions
- From 9.0 on, Red Hat publishes the current RHCS 9 documentation as PDF only. The older RHCS 9 HTML pages
  (html-single guides under docs.redhat.com/.../red_hat_ceph_storage/9/) are marked deprecated and no longer maintained:
  prefer the PDFs below.
- RHCS 9 minor releases: 9.0, 9.1, 9.2, each with asynchronous z-stream updates (for example 9.0z1, 9.0z2, 9.0z3)
  covered in that minor release's release notes. Pick the guide for the installed minor release.
- The 9.0 publications are hosted on IBM Docs; 9.1 and 9.2 PDFs are on access.redhat.com.

## RHCS 9.2
| Guide | What it covers | PDF |
|---|---|---|
| Release Notes 9.2 | New features, known issues, bug fixes of 9.2 | https://access.redhat.com/sites/default/files/attachments/red_hat_ceph_storage_release_notes_1.pdf |
| User Guide 9.2 | The complete 9.2 documentation in one PDF | https://access.redhat.com/sites/default/files/attachments/red_hat_ceph_storage_user_guide_3.pdf |

## RHCS 9.1
| Guide | What it covers | PDF |
|---|---|---|
| Release Notes 9.1 | 9.1 and its asynchronous updates | https://access.redhat.com/sites/default/files/attachments/red_hat_ceph_storage_release_notes.pdf |
| User Guide 9.1 | The complete 9.1 documentation in one PDF | https://access.redhat.com/sites/default/files/attachments/red_hat_ceph_storage_user_guide_0.pdf |

Topic PDFs for 9.1 (all under https://access.redhat.com/sites/default/files/attachments/):
| Guide | What it covers | File |
|---|---|---|
| Compatibility | Supported products and versions alongside RHCS (backup targets, identity providers, S3 archive endpoints, OpenStack, ODF) | `red_hat_ceph_storage_compatibility_0.pdf` |
| Getting Started | First steps and basic features | `red_hat_ceph_storage_getting_started_0.pdf` |
| Overview | Architecture, data security and hardening | `red_hat_ceph_storage_overview_0.pdf` |
| Planning | Support matrix, hardware and storage strategy prerequisites | `red_hat_ceph_storage_planning_0.pdf` |
| Installing | Installing on RHEL (AMD64 / Intel 64), cephadm | `installing_red_hat_ceph_storage_0.pdf` |
| Upgrading | Upgrading a cluster on RHEL (AMD64 / Intel 64) | `upgrading_red_hat_ceph_storage_0.pdf` |
| Configuring | Ceph configuration options | `configuring_red_hat_ceph_storage_0.pdf` |
| Edge Clusters | Small, cost-efficient object storage configurations | `red_hat_ceph_storage_edge_clusters_0.pdf` |
| Administering | Day-to-day administration and operations (OSDs, pools, PGs, health) | `administering_red_hat_ceph_storage_0.pdf` |
| Dashboard | Ceph Dashboard administration, configuration and monitoring | `red_hat_ceph_storage_dashboard_0.pdf` |
| Ceph Object Gateway | RGW deployment, configuration, administration, S3, multisite | `red_hat_ceph_storage_object_gateways_0.pdf` |
| NFS Cluster and Share Management | NFS clusters exporting CephFS (OpenStack Manila users only) | `red_hat_ceph_storage_nfs_cluster_and_share_management_openstack_manila_users_only_0.pdf` |
| File Systems | MDS configuration, creating and mounting CephFS | `red_hat_ceph_storage_file_systems_0.pdf` |
| Block Devices | RBD management and use | `red_hat_ceph_storage_block_devices_0.pdf` |
| Block Devices and OpenStack | Ceph and OpenStack integration models | `red_hat_ceph_storage_block_devices_and_openstack_0.pdf` |
| Developer | RHCS APIs | `red_hat_ceph_storage_developer_0.pdf` |
| Troubleshooting | First-line troubleshooting before opening a Red Hat support case | `red_hat_ceph_storage_troubleshooting_0.pdf` |

## RHCS 9.0
| Guide | What it covers | Where |
|---|---|---|
| Release Notes 9.0 | 9.0 and its asynchronous updates (9.0z1 to 9.0z3 at cataloguing time), security fixes | https://www.ibm.com/docs/en/SSEG27_9.9.0/out/90/Red_Hat_Ceph_Storage_9.0_Release_Notes.pdf |
| 9.0 publications | Full and chapter-level 9.0 PDFs | https://www.ibm.com/docs/en/storage-ceph/9.9.0?topic=red-hat-ceph-storage-90-publications |

## Adding the PDFs themselves
Red Hat's download server refused the library's build machine. From a machine with internet access, download the PDFs
above into this folder (`docs/redhat/rhcs-9/`), keeping Red Hat's file names, then commit and push; with the VM docs
service, re-run `sudo python3 vm-setup.py` on the VM. Indexing PDFs needs the `pypdf` package (LIBRARY.md).
