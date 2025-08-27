# Ansible - Custom Roles

These roles are specialised to my home network. I try to keep them isolated from each other, but it's best effort. If you copy and paste them out to your own project they _might_ run well for you, but I can't guarantee it.

The roles here are designed to be run on Ubuntu, as that's what I use everywhere.

There are also a bunch of first and third-party roles [installed via the Ansible Galaxy system](../meta/).

## Ansible

Specialised roles to allow Ansible-related tasks to run on a host.

## Bootstrap

Bootstrap a host with common functionality.

## Client

These roles install client software that work in conjunction with a dedicated server.

## Compositions

Generally container-based applications that aren't offered by the host OS. They tend to offer a web interface.

## Hardware

Roles to support specific hardware configurations.

## Infra

Specialised roles that provide infrastructure that keeps all hosts running.

## Monitoring

Roles that provide enable of the host.

## Network

Network-related roles.

## Server

These roles install server software that work in conjunction with specialised clients.

## System

Generic system-level roles.

## User

If a specialised user is needed, one of these roles will install it.

## Virtual

Anything related to virtualisation, either at a host or guest level.

## ZFS

ZFS is specialised enough to warrant its own role.
