# MGC YFC Operations 0.29.0

- Closes the page dropdown when the desktop mouse leaves it, on outside clicks/taps, and on Escape.
- Routes Dispatch Reports to pickup/delivery reports and Receipts Reports to a separate green receipt-report page.
- Adds a receipt-page divider and receipt illustration, Upload a Receipt, and View My Receipts. Signed-in uploads belong to the employee profile and can be searched by filename, uploader, category and dates. Search results have pagination and a print view.
- Administrators can view all receipts. The new employee permission View all users' receipts (manager/accounting) delegates that access. Anonymous uploads remain separate from employee profiles; recreating an employee account does not inherit the old account's receipts.
- Uses dark backgrounds for empty appointment blocks in This Week and Next Week.
- Keeps the combined server's Administration sign-in across application/server restarts using a Windows-protected local session. It expires when the application version changes. Sign-out, account removal and password resets also revoke access. Browser sessions keep their existing daily limits; local administration remains restricted to the server computer.
- Moves the replay link below Share YFC with Someone and shows sharing on desktop as well as mobile.
- Adds Application Settings > Sharing for separate mobile/desktop Text, Email and native-sharing switches. Mobile Text/Email open the default apps. Desktop Text offers a messaging-app prompt; desktop Email offers a local mail app or Gmail/Outlook in a new browser tab.

Use the full Windows installer on the server to receive the Administration sign-in changes. Exit the server from its tray menu, install over the existing location, select Server, restart and refresh browsers. Do not uninstall the server first.

The in-app update ZIP delivers the receipt, reporting, sharing and web/API changes. Desktop applications remain unsigned; code signing is still deferred.
