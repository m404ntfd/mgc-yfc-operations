"""Real TLS checks with disposable certificates; no production credentials or data."""
import datetime as dt
import ipaddress
import ssl
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
import desktop_update_security as security
import pos_updater


class UpdateCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.now = dt.datetime.now(dt.timezone.utc)
        cls.authorities = {}
        for label in ('system', 'bundle', 'untrusted'):
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, label+' test CA')])
            cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                    .public_key(key.public_key()).serial_number(x509.random_serial_number())
                    .not_valid_before(cls.now-dt.timedelta(days=1)).not_valid_after(cls.now+dt.timedelta(days=2))
                    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                    .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, None, None), critical=True)
                    .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
                    .sign(key, hashes.SHA256()))
            path = cls.root/(label+'.pem');path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            cls.authorities[label] = (key, cert, path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def endpoint(self, authority='bundle', *, wrong_name=False, expired=False):
        ca_key, ca, _ = self.authorities[authority]
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost fixture')])
        names = [x509.DNSName('wrong.invalid')] if wrong_name else [x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(ca.subject)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(self.now-dt.timedelta(days=2))
                .not_valid_after(self.now+dt.timedelta(days=-1 if expired else 1))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, None, None), critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .add_extension(x509.SubjectAlternativeName(names), critical=False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
                .sign(ca_key, hashes.SHA256()))
        cert_path=self.root/'server.pem';key_path=self.root/'server.key'
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200);self.end_headers();self.wfile.write(b'verified fixture')
            def log_message(self, *args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert_path,key_path)
        server.socket=context.wrap_socket(server.socket,server_side=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def stop():server.shutdown();server.server_close();thread.join(timeout=2)
        self.addCleanup(stop)
        return 'https://127.0.0.1:'+str(server.server_port)+'/fixture'

    def client_context(self, system=True):
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if system:context.load_verify_locations(cafile=str(self.authorities['system'][2]))
        return context

    def test_system_roots_and_bundled_roots_both_remain_trusted(self):
        for authority in ('system','bundle'):
            with self.subTest(authority=authority):
                url=self.endpoint(authority)
                context=self.client_context()
                with patch.object(security.ssl,'create_default_context',return_value=context),patch.object(security.certifi,'where',return_value=str(self.authorities['bundle'][2])):
                    self.assertEqual(pos_updater.fetch(url),b'verified fixture')
                self.assertTrue(context.check_hostname)
                self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)

    def test_bundle_works_with_empty_default_store(self):
        url=self.endpoint()
        with patch.object(security.ssl,'create_default_context',return_value=self.client_context(False)),patch.object(security.certifi,'where',return_value=str(self.authorities['bundle'][2])):
            self.assertEqual(pos_updater.fetch(url),b'verified fixture')

    def test_untrusted_expired_and_wrong_host_certificates_are_rejected(self):
        for options in ({'authority':'untrusted'},{'expired':True},{'wrong_name':True}):
            with self.subTest(options=options):
                url=self.endpoint(**options)
                with patch.object(security.ssl,'create_default_context',return_value=self.client_context()),patch.object(security.certifi,'where',return_value=str(self.authorities['bundle'][2])):
                    with self.assertRaises(URLError) as caught:pos_updater.fetch(url)
                self.assertIsInstance(caught.exception.reason,ssl.SSLCertVerificationError)

    def test_missing_bundle_fails_closed(self):
        with patch.object(security.certifi,'where',return_value=str(self.root/'missing.pem')):
            with self.assertRaises(OSError):security.update_ssl_context()

    def test_clear_certificate_error_and_ordinary_errors(self):
        for error in (ssl.SSLCertVerificationError('issuer missing'),URLError(ssl.SSLCertVerificationError('issuer missing'))):
            message=security.update_error_message(error)
            self.assertIn('security certificate',message)
            self.assertIn('No update was installed',message)
            self.assertNotIn('_ssl.c',message)
        self.assertEqual(security.update_error_message(ValueError('Download failed')),'Download failed')


if __name__=='__main__':unittest.main()
