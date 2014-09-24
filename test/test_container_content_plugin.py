#
# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import mock

import fixture
import tempfile
import shutil
import os.path

from subscription_manager.model import Content, Entitlement, EntitlementSource
from subscription_manager.model.ent_cert import EntitlementCertContent
from subscription_manager.plugin.container.action_invoker import \
    ContainerContentUpdateActionCommand, KeyPair, ContainerCertDir

from rhsm import certificate2

DUMMY_CERT_LOCATION = "/dummy/certs"


class TestContainerContentUpdateActionCommand(fixture.SubManFixture):

    def _create_content(self, label, cert):
        return Content("containerImage", label, label, cert=cert)

    def _mock_cert(self, base_filename):
        cert = mock.Mock()
        cert.path = "%s/%s.pem" % (DUMMY_CERT_LOCATION, base_filename)
        cert.key_path.return_value = "%s/%s-key.pem" %  \
            (DUMMY_CERT_LOCATION, base_filename)
        return cert

    def test_unique_paths_with_dupes(self):
        cert1 = self._mock_cert('5001')
        cert2 = self._mock_cert('5002')
        cert3 = self._mock_cert('5003')

        content1 = self._create_content('content1', cert1)
        content2 = self._create_content('content2', cert1)
        content3 = self._create_content('content3', cert2)

        # This content is provided by two other certs:
        content1_dupe = self._create_content('content1', cert2)
        content1_dupe2 = self._create_content('content1', cert3)

        contents = [content1, content2, content3, content1_dupe,
            content1_dupe2]
        cmd = ContainerContentUpdateActionCommand(None, 'cdn.example.org')
        cert_paths = cmd._get_unique_paths(contents)
        self.assertEquals(3, len(cert_paths))
        self.assertTrue(KeyPair(cert1.path, cert1.key_path()) in cert_paths)
        self.assertTrue(KeyPair(cert2.path, cert2.key_path()) in cert_paths)
        self.assertTrue(KeyPair(cert3.path, cert3.key_path()) in cert_paths)


class TestContainerContents(fixture.SubManFixture):

    def create_content(self, content_type, name):
        content = certificate2.Content(
            content_type=content_type,
            name="mock_content_%s" % name,
            label=name,
            enabled=True,
            gpg="path/to/gpg",
            url="http://mock.example.com/%s/" % name)
        return EntitlementCertContent.from_cert_content(content)

    def test_find_container_content(self):
        yum_content = self.create_content("yum", "yum_content")
        container_content = self.create_content("containerImage",
            "container-content")

        ent1 = Entitlement(contents=[yum_content])
        ent2 = Entitlement(contents=[container_content])

        ent_src = EntitlementSource()
        ent_src._entitlements = [ent1, ent2]


class TestKeyPair(fixture.SubManFixture):

    def test_expected_filenames(self):
        kp = KeyPair("/etc/pki/entitlement/9000.pem",
            "/etc/pki/entitlement/9000-key.pem")
        self.assertEquals("9000.cert", kp.dest_cert_filename)
        self.assertEquals("9000-key.key", kp.dest_key_filename)

    def test_expected_filenames_weird_extensions(self):
        kp = KeyPair("/etc/pki/entitlement/9000.crt",
            "/etc/pki/entitlement/9000-key.crt")
        self.assertEquals("9000.cert", kp.dest_cert_filename)
        self.assertEquals("9000-key.key", kp.dest_key_filename)

    def test_expected_filenames_weird_filenames(self):
        kp = KeyPair("/etc/pki/entitlement/9000.1.2014-a.pem",
            "/etc/pki/entitlement/9000.1.2014-a-key.pem")
        self.assertEquals("9000.1.2014-a.cert", kp.dest_cert_filename)
        self.assertEquals("9000.1.2014-a-key.key", kp.dest_key_filename)


class TestContainerCertDir(fixture.SubManFixture):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='subman-container-plugin-tests')
        self.src_certs_dir = os.path.join(self.temp_dir, "etc/pki/entitlement")
        os.makedirs(self.src_certs_dir)

        # This is where we'll setup for container certs:
        container_dir = os.path.join(self.temp_dir,
            "etc/docker/certs.d/")

        # Where we expect our certs to actually land:
        self.dest_dir = os.path.join(container_dir, 'cdn.example.org')
        self.container_dir = ContainerCertDir('cdn.example.org',
            path=container_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _touch(self, dir_path, filename):
        """
        Create an empty file in the given directory with the given filename.
        """
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        open(os.path.join(dir_path, filename), 'a').close()

    def test_created_if_missing(self):
        # Doesn't exist yet:
        self.assertFalse(os.path.exists(self.dest_dir))
        self.container_dir.sync([])
        self.assertTrue(os.path.exists(self.dest_dir))

    def test_first_install(self):
        cert1 = '1234.pem'
        key1 = '1234-key.pem'
        self._touch(self.src_certs_dir, cert1)
        self._touch(self.src_certs_dir, key1)
        kp = KeyPair(os.path.join(self.src_certs_dir, cert1),
            os.path.join(self.src_certs_dir, key1))
        self.container_dir.sync([kp])
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, '1234.cert')))
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, '1234-key.key')))

    def test_old_certs_cleaned_out(self):
        cert1 = '1234.cert'
        key1 = '1234-key.key'
        ca = 'myca.crt'  # This file extension should be left alone:
        self._touch(self.dest_dir, cert1)
        self._touch(self.dest_dir, key1)
        self._touch(self.dest_dir, ca)
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, '1234.cert')))
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, '1234-key.key')))
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, ca)))
        self.container_dir.sync([])
        self.assertFalse(os.path.exists(os.path.join(self.dest_dir, '1234.cert')))
        self.assertFalse(os.path.exists(os.path.join(self.dest_dir, '1234-key.key')))
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, ca)))
