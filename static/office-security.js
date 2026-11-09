// OFFICE owns shared account administration; STORE OPS keeps staff self-service.
if(officeSecurityPage){
 document.body.classList.add('officeSecurityEmbed');document.title='CoastYouth Retail OFFICE · Users & roles';
 const securityLandingBefore=chooseLanding;
 chooseLanding=async function(){
  if(!user)return;
  tab('settings');settingsSection(4);
  selectUserSettings(location.hash==='#retail-roles'?'roles':'users');
 };
}
