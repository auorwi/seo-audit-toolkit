from support import InventoryTest


class NetworkTests(InventoryTest):
    def test_rejects_nonpublic_dns_answers_including_mixed_public_private(self):
        check = self.module("network").validate_addresses
        for addresses in [["127.0.0.1"], ["10.1.2.3"], ["169.254.169.254"], ["::1"],
                          ["fc00::1"], ["8.8.8.8", "192.168.1.1"], []]:
            with self.subTest(addresses=addresses), self.assertRaises(ValueError):
                check(addresses)

    def test_accepts_public_addresses(self):
        check = self.module("network").validate_addresses
        self.assertEqual(check(["8.8.8.8", "2606:4700:4700::1111"]), ["8.8.8.8", "2606:4700:4700::1111"])

    def test_outside_scope_rejected_before_network(self):
        client = self.module("network").HttpClient(["bingx.com"], delay=0)
        with self.assertRaises(ValueError):
            client.get("https://example.com/")

    def test_safe_headers_exclude_cookie_and_auth_values(self):
        clean = self.module("network").safe_headers
        result = clean({"Set-Cookie": "sid=secret", "Authorization": "Bearer secret", "Content-Type": "text/html",
                        "Location": "https://bingx.com/?token=secret", "ETag": '"v1"'})
        self.assertNotIn("secret", str(result))
        self.assertEqual(result["content-type"], "text/html")
        self.assertEqual(result["etag"], '"v1"')

    def test_system_alias_dns_is_opt_in_https_only_and_never_all_private_ranges(self):
        check = self.module("network").validate_addresses
        with self.assertRaises(ValueError):
            check(["198.18.1.182"])
        self.assertEqual(check(["198.18.1.182"], allow_benchmark_alias=True, scheme="https"), ["198.18.1.182"])
        for addresses, scheme in [(["198.18.1.182"], "http"), (["127.0.0.1"], "https"),
                                  (["169.254.169.254"], "https"), (["198.18.1.182", "10.0.0.1"], "https")]:
            with self.subTest(addresses=addresses, scheme=scheme), self.assertRaises(ValueError):
                check(addresses, allow_benchmark_alias=True, scheme=scheme)
