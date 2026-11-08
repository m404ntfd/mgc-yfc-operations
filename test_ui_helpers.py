def password_login_page(page):
 toggle=page.locator("#deskPasswordToggle")
 if toggle.is_visible() and not page.locator("#login").is_visible():toggle.click()
 return page
