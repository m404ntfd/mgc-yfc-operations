# YFC Store Management 0.20.2

Fix Invalid origin during login and saves through Cloudflare Tunnel HTTPS. The server trusts the HTTPS scheme only from a connector on the same computer, keeps exact Host/Origin matching, and marks HTTPS session cookies Secure. Local network HTTP access remains supported. Initial administrator setup is blocked through proxy connections.

Install the update using the local server address, then reopen https://operations.coastyfc.com. Keep Cloudflare Access enabled for approved staff. The tunnel must run on the dispatch server and target http://localhost:8080 without overriding the HTTP Host header.
