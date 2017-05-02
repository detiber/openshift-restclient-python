# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import re
import copy
import io
import os
import tarfile
import time
import uuid
import yaml

import docker
import pytest
import requests
import json

from pkg_resources import parse_version

from openshift.client import models
from kubernetes.client import V1Namespace, V1ObjectMeta
from openshift.helper.ansible import KubernetesAnsibleModuleHelper, OpenShiftAnsibleModuleHelper

if os.path.exists(os.path.join(os.getcwd(), 'KubeObjHelper.log')):
    os.remove(os.path.join(os.getcwd(), 'KubeObjHelper.log'))


@pytest.fixture(scope='session')
def openshift_container(request):
    client = docker.from_env()
    # TODO: bind to a random host port
    openshift_version = request.config.getoption('--openshift-version')
    if openshift_version is None:
        yield None
    else:
        image_name = 'openshift/origin:{}'.format(openshift_version)
        container = client.containers.run(image_name, 'start master', detach=True,
                                          ports={'8443/tcp': 8443})

        try:
            # Wait for the container to no longer be in the created state before
            # continuing
            while container.status == u'created':
                time.sleep(0.2)
                container = client.containers.get(container.id)

            # Wait for the api server to be ready before continuing
            for _ in range(10):
                try:
                    requests.head("https://127.0.0.1:8443/healthz/ready", verify=False)
                except requests.RequestException:
                    pass
                time.sleep(1)

            time.sleep(1)

            yield container
        finally:
            # Always remove the container
            container.remove(force=True)


@pytest.fixture(scope='session')
def kubeconfig(openshift_container, tmpdir_factory):
    # get_archive returns a stream of the tar archive containing the requested
    # files/directories, so we need use BytesIO as an intermediate step.
    if openshift_container is None:
        return None
    else:
        openshift_container.exec_run('oc login -u test -p test')
        tar_stream, _ = openshift_container.get_archive(
            '/var/lib/origin/openshift.local.config/master/admin.kubeconfig')
        tar_obj = tarfile.open(fileobj=io.BytesIO(tar_stream.read()))
        kubeconfig_contents = tar_obj.extractfile('admin.kubeconfig').read()

        kubeconfig_file = tmpdir_factory.mktemp('kubeconfig').join('admin.kubeconfig')
        kubeconfig_file.write(kubeconfig_contents)
        return kubeconfig_file


@pytest.fixture(scope='session')
def admin_kubeconfig(openshift_container, tmpdir_factory):
    # get_archive returns a stream of the tar archive containing the requested
    # files/directories, so we need use BytesIO as an intermediate step.
    if openshift_container is None:
        return None
    else:
        openshift_container.exec_run('oc login -u system:admin')
        tar_stream, _ = openshift_container.get_archive(
            '/var/lib/origin/openshift.local.config/master/admin.kubeconfig')
        tar_obj = tarfile.open(fileobj=io.BytesIO(tar_stream.read()))
        kubeconfig_contents = tar_obj.extractfile('admin.kubeconfig').read()

        kubeconfig_file = tmpdir_factory.mktemp('kubeconfig').join('admin.kubeconfig')
        kubeconfig_file.write(kubeconfig_contents)
        return kubeconfig_file


@pytest.fixture(scope='class')
def ansible_helper(request, kubeconfig, admin_kubeconfig):
    pieces = re.findall('[A-Z][a-z0-9]*', request.node.name)
    api_version = pieces[1].lower()
    resource = '_'.join(map(str.lower, pieces[2:]))
    needs_admin = request.node.cls.tasks.get('admin')
    config = admin_kubeconfig if needs_admin else kubeconfig
    auth = {}
    if kubeconfig is not None:
        auth = {
            'kubeconfig': str(config),
            'host': 'https://localhost:8443',
            'verify_ssl': False
        }
    try:
        helper = KubernetesAnsibleModuleHelper(api_version, resource, debug=True, reset_logfile=False, **auth)
    except Exception:
        helper = OpenShiftAnsibleModuleHelper(api_version, resource, debug=True, reset_logfile=False, **auth)

    helper.api_client.config.debug = True

    return helper


@pytest.fixture(scope='session')
def obj_compare():
    def compare_func(ansible_helper, k8s_obj, parameters):
        """ Assert that an object matches an expected object """
        requested = copy.deepcopy(k8s_obj)
        ansible_helper.object_from_params(parameters, obj=requested)

        ansible_helper.log('paramters:')
        ansible_helper.log(json.dumps(parameters, indent=4))
        ansible_helper.log('\n\n')

        ansible_helper.log('k8s_obj:')
        ansible_helper.log(json.dumps(k8s_obj.to_dict(), indent=4))
        ansible_helper.log('\n\n')

        ansible_helper.log('from params:')
        ansible_helper.log(json.dumps(requested.to_dict(), indent=4))
        ansible_helper.log('\n\n')

        match, diff = ansible_helper.objects_match(k8s_obj, requested)
        if not match:
            ansible_helper.log('\n\n')
            ansible_helper.log('Differences:')
            ansible_helper.log(json.dumps(diff, indent=4))
            ansible_helper.log('\n\n')
        assert match

    return compare_func


@pytest.fixture(scope='class')
def namespace(kubeconfig):
    name = "test-{}".format(uuid.uuid4())

    auth = {}
    if kubeconfig is not None:
        auth = {
            'kubeconfig': str(kubeconfig),
            'host': 'https://localhost:8443',
            'verify_ssl': False
        }
    helper = KubernetesAnsibleModuleHelper('v1', 'namespace', debug=True, reset_logfile=False, **auth)

    k8s_obj = helper.create_object(V1Namespace(metadata=V1ObjectMeta(name=name)))
    assert k8s_obj is not None

    yield name

    helper.delete_object(name, None)


@pytest.fixture()
def object_name(request):
    action = request.function.__name__.split('_')[1]
    return '{}-{}'.format(action, uuid.uuid4())[:22].strip('-')


@pytest.fixture(scope='class')
def project(kubeconfig):
    name = "test-{}".format(uuid.uuid4())
    auth = {}
    if kubeconfig is not None:
        auth = {
            'kubeconfig': str(kubeconfig),
            'host': 'https://localhost:8443',
            'verify_ssl': False
        }
    helper = OpenShiftAnsibleModuleHelper('v1', 'project', debug=True, reset_logfile=False, **auth)

    k8s_obj = helper.create_project(metadata=V1ObjectMeta(name=name))
    assert k8s_obj is not None

    yield name

    helper.delete_object(name, None)


@pytest.fixture
def openshift_version():
    return pytest.config.getoption('--openshift-version')


@pytest.fixture(autouse=True)
def skip_by_version(request, openshift_version):
    if request.node.cls.tasks.get('version_limits') and openshift_version:
        lowest_version = str(request.node.cls.tasks['version_limits'].get('min'))
        highest_version = str(request.node.cls.tasks['version_limits'].get('max'))
        skip_latest = request.node.cls.tasks['version_limits'].get('latest')

        if openshift_version == 'latest':
            if skip_latest:
                pytest.skip('This API is not supported in the latest openshift version')
            return

        too_low = lowest_version and parse_version(lowest_version) > parse_version(openshift_version)
        too_high = highest_version and parse_version(highest_version) < parse_version(openshift_version)

        if too_low or too_high:
            pytest.skip('This API is not supported in openshift versions < {}'.format(openshift_version))


def _get_id(argvalue):
    op_type = ''
    if argvalue.get('create'):
        op_type = 'create'
    elif argvalue.get('patch'):
        op_type = 'patch'
    elif argvalue.get('remove'):
        op_type = 'remove'
    elif argvalue.get('replace'):
        op_type = 'replace'
    return op_type + '_' + argvalue[op_type]['name'] + '_' + "{:0>3}".format(argvalue['seq'])


# def pytest_generate_tests(metafunc):
#     tasks = {'create': [], 'remove': [], 'patch': [], 'replace': []}
#     for task in metafunc.cls.tasks:
#         for action in ['create', 'patch', 'remove', 'replace']:
#             if '{}_tasks'.format(action) in metafunc.fixturenames:
#                 tasks[action].append(task)

#     # TODO: might need to update this...
#     if 'namespaces' in metafunc.fixturenames:
#         tasks = [x for x in tasks['create'] if x.get('namespace')]
#         unique_namespaces = dict()
#         for task in tasks:
#             unique_namespaces[task['create']['namespace']] = None
#         metafunc.parametrize("namespaces", list(unique_namespaces.keys()))
