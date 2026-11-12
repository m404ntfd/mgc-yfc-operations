def select_saved_sale(page,ident):
 page.locator('#posFindCart').click()
 page.locator('[data-saved-sale="'+ident+'"]').click()
 page.locator('#checkoutResume').click()

def password_login_page(page):
 toggle=page.locator("#deskPasswordToggle")
 if toggle.is_visible() and not page.locator("#login").is_visible():toggle.click()
 return page

def office_setting(page, action):
 """Find a permitted setting through the visible category and group controls."""
 from playwright.sync_api import expect
 page.locator('#officeSettingsSearch').wait_for(state='visible')
 info=page.evaluate("""action=>{action=officeNavigationAliases[action]||action;
 const group=officeNavigationGroups.find(g=>g.actions.includes(action));
 return {action,group:group?.id,section:group?.section,allowed:officeMenuCards().some(c=>c.action===action)};}""",action)
 target=page.locator('#officeTiles [data-office-action="'+info['action']+'"]')
 if not info['allowed'] or target.is_visible():return target
 page.locator('#officeNav [data-office-section="'+info['section']+'"]').click()
 page.locator('#officeGroups [data-office-group="'+info['group']+'"]').click()
 expect(target).to_be_visible()
 return target


def wait_for_pos_save(page):
 """Wait for a serial checkout action and its server refresh to finish."""
 for _ in range(100):
  if page.evaluate('!posBusy && !posPending && !flowProductStarting'):return
  page.wait_for_timeout(50)
 raise AssertionError('The checkout action did not finish saving and refreshing.')
