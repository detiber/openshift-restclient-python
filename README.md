# OpenShift python client

[![Build Status](https://travis-ci.org/openshift/openshift-restclient-python.svg?branch=master)](https://travis-ci.org/openshift/openshift-restclient-python)
[![Coverage Status](https://coveralls.io/repos/github/openshift/openshift-restclient-python/badge.svg?branch=master)](https://coveralls.io/github/openshift/openshift-restclient-python?branch=master)

Python client for the [OpenShift](http://openshift.redhat.com/) API.

## Installation

From source:

```
git clone https://github.com/openshift/openshift-restclient-python.git
cd openshift-restclient-python
python setup.py install
```

From [PyPi](https://pypi.python.org/pypi/openshift/) directly (coming soon):

```
pip install openshift
```

## Example

TODO

## Documentation

All APIs and Models' documentation can be found at the [Generated client's README file](openshift/README.md)

## Community, Support, Discussion

If you have any problem with the package or any suggestions, please file an [issue](https://github.com/openshift/openshift-restclient-python/issues).

### Code of Conduct

Participation in the Kubernetes community is governed by the [CNCF Code of Conduct](https://github.com/cncf/foundation/blob/master/code-of-conduct.md).

## Update generated client
Updating the generated client requires the following tools:
- tox
- maven3

1) Incorporate new changes to update scripts
  - scripts/constants.py, scripts/pom.xml, scripts/preprocess_spec.py, update-client.sh are the most important
1) Run tox -e update_client

## Ansible Modules

This repo is home to the tools used to generate the K8s modules for Ansible.

### Using the modules

The modules are currently in pre-release. For convenience there is an Ansible role available at [ansible/ansible-kubernetes-modules](https://github.com/ansible/ansible-kubernetes-modules), which if referenced in a playbook, will provide full access to the latest.

#### Requirements

- Ansible installed [from source](http://docs.ansible.com/ansible/intro_installation.html#running-from-source)
- OpenShift Rest Client installed on the host where the modules will execute

#### Installation and use

Using the Galaxy client, download and install the role as follows:

```
$ ansible-galaxy install ansible.kubernetes-modules
```

Include the role in your playbook, and the modules will be available, allowing tasks from any other play or role to reference them. Here's an example:

```
- hosts: localhost
  connection: local
  gather_facts: no
  roles:
    - role: ansible.kubernetes-modules
    - role: hello-world
```

The `hello-world` role deploys an application to a locally running OpenShift instance by executing tasks with the modules. It's able to access them because `ansible.ansible-kubernetes-modules` is referenced.  

You'll find the modules in the [library](https://github.com/ansible/ansible-kubernetes-modules/tree/master/library) folder of the role. Each contains documented parameters, and the returned data structure. Not every module contains examples, only those where we have added [test data](./openshift/ansiblegen/examples).

If you find a bug, or have a suggestion, related to the modules, please [file an issue here](https://github.com/openshift/openshift-restclient-python/issues) 

### Generating the modules

After installing the OpenShift client, the modules can be generated by running the following:

```
$ openshift-ansible-gen modules --output-path /path/to/modules/dir
```

If `--output-path` is not provided, modules will be written to `./_modules`.

### Common module

Individual modules are generated using the OpenShift Rest Client. However, there is a shared or utility module in the [Ansible repo](https://github.com/ansible/ansible) called, *k8s_common.py*, which imports the client, and performs most of the work. This is currently in a pre-release state as well, and is only available in the `devel` branch of Ansible. For this reason, you'll need to run Ansible from source. For assistnace, see [Running from source](http://docs.ansible.com/ansible/intro_installation.html#running-from-source). 
