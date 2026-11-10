# Linux kernel administration guide

This is a landing page or contents index. Linked documents are not part of this individual snapshot.

English

- Chinese (Simplified)

- Chinese (Traditional)

- Portuguese (Brazilian)

# The Linux kernel user’s and administrator’s guide¶

The following is a collection of user-oriented documents that have been
added to the kernel over time. There is, as yet, little overall order or
organization here — this material was not written to be a single, coherent
document! With luck things will improve quickly over time.

## General guides to kernel administration¶

This initial section contains overall information, including the README
file describing the kernel as a whole, documentation on kernel parameters,
etc.

- Linux kernel release 6.x <http://kernel.org/>

- Linux allocated devices (4.x+ version)

- Feature status on all architectures

A big part of the kernel’s administrative interface is the /proc and sysfs
virtual filesystems; these documents describe how to interact with tem

- Rules on how to access information in sysfs

- Documentation for /proc/sys

- How CPU topology info is exported via sysfs

- Linux ABI description

Security-related documentation:

- Hardware vulnerabilities

- Linux Security Module Usage

- Perf events and tool security

## Booting the kernel¶

- Boot Configuration

- The kernel’s command-line parameters

- The EFI Boot Stub

- Using the initial RAM disk (initrd)

## Tracking down and identifying problems¶

Here is a set of documents aimed at users who are trying to track down
problems and bugs in particular.

- Reporting issues

- Reporting regressions

- How to quickly build a trimmed Linux kernel

- How to verify bugs and bisect regressions

- Bug hunting

- Bisecting a regression

- Tainted kernels

- Ramoops oops/panic logger

- Dynamic debug

- Explaining the “No working init found.” boot hang message

- Documentation for Kdump - The kexec-based Crash Dumping Solution

- Performance monitor support

- pstore block oops/panic logger

- Clearing WARN_ONCE

- Reducing OS jitter due to per-cpu kthreads

- Softlockup detector and hardlockup detector (aka nmi_watchdog)

- Reliability, Availability and Serviceability (RAS)

- Error decoding

- Address translation

- Linux Magic System Request Key Hacks

## Core-kernel subsystems¶

These documents describe core-kernel administration interfaces that are
likely to be of interest on almost any system.

- Control Group v2

- Control Groups version 1

- CPU Isolation

- CPU load

- Memory Management

- Kernel module signing facility

- Namespaces

- Numa policy hit/miss statistics

- Power Management

- Syscall User Dispatch

Support for non-native binary formats. Note that some of these
documents are ... old ...

- Kernel Support for miscellaneous Binary Formats (binfmt_misc)

- Java(tm) Binary Kernel Support for Linux v1.03

- Mono(tm) Binary Kernel Support for Linux

## Block-layer and filesystem administration¶

- A block layer cache (bcache)

- The Android binderfs Filesystem

- Block Devices

- CIFS

- Device Mapper

- ext4 General Information

- File system Monitoring with fanotify

- NFS

- I/O statistics fields

- IBM’s Journaled File System (JFS) for Linux

- RAID arrays

- Using UFS

- The SGI XFS Filesystem

## Device-specific guides¶

How to configure your hardware within your Linux system.

- ACPI Support

- ATA over Ethernet (AoE)

- Auxiliary Display Support

- Linux Braille Console

- btmrvl driver

- Dell Remote BIOS Update driver (dell_rbu)

- EDID

- GPIO

- Hardware random number generators

- Laptop Drivers

- Parallel port LCD/Keypad Panel support

- Media subsystem admin and user guide

- Linux NVMe multipath

- Parport

- Linux Plug and Play Documentation

- RapidIO Subsystem Guide

- Real Time Clock (RTC) Drivers for Linux

- Linux Serial Console

- Video Mode Selection Support 2.13

- Thermal Subsystem

- USB4 and Thunderbolt

- Software cursor for VGA

- Video Output Switcher Control

## Workload analysis¶

This is the beginning of a section with information of interest to
application developers and system integrators doing analysis of the
Linux kernel for safety critical applications. Documents supporting
analysis of kernel interactions with applications, and key kernel
subsystems expectations will be found here.

- Discovering Linux kernel subsystems used by a workload

## Everything else¶

A few hard-to-categorize and generally obsolete documents.

- LDM - Logical Disk Manager (Dynamic Disks)

- Unicode support
