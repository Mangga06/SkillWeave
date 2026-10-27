import {test,expect} from '@playwright/test';
test('seeded work history is visible to volunteers and coordinators',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/login');await page.getByLabel('Email address').fill('volunteer@demo.skillweave.test');await page.getByLabel('Password',{exact:true}).fill('WeaveDemo!2026');await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('link',{name:'Skills & availability'}).click();
 await expect(page.getByRole('heading',{name:'Project contributions & work history'})).toBeVisible();
 await expect(page.getByRole('link',{name:'Riverbank renewal'})).toBeVisible();
 await expect(page.getByText('4 completed projects',{exact:true})).toBeVisible();
 await page.screenshot({path:'test-results/volunteer-work-history.png',fullPage:true});
 await page.goto('/login');await page.getByLabel('Email address').fill('coordinator@demo.skillweave.test');await page.getByLabel('Password',{exact:true}).fill('WeaveDemo!2026');await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('link',{name:'Volunteer directory'}).click();await page.getByRole('button',{name:/Avery Patel/}).click();
 await expect(page.getByRole('dialog').getByRole('link',{name:'Community harvest festival'})).toBeVisible();
 await expect(page.getByRole('dialog').getByText('4 completed projects',{exact:true})).toBeVisible();
 expect(errors).toEqual([]);
});
test('coordinator theme, navigation, optimization and exports',async({page})=>{
 await page.goto('/login');await page.getByLabel('Email address').fill('coordinator@demo.skillweave.test');await page.getByLabel('Password',{exact:true}).fill('WeaveDemo!2026');await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Good to see you, Sam.'})).toBeVisible();
 await page.getByLabel('Theme preference').selectOption('dark');await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.screenshot({path:'test-results/coordinator-dark.png',fullPage:true});
 await page.getByRole('link',{name:/Optimization Lab/}).first().click();await page.getByLabel('Population',{exact:true}).fill('8');await page.getByLabel('Generations',{exact:true}).fill('3');await page.getByRole('button',{name:'Run optimization',exact:true}).click();
 await expect(page.getByText('Evolution of a better fit')).toBeVisible({timeout:45000});await expect(page.getByRole('button',{name:'Publish invitations'})).toBeVisible();
 await page.getByLabel('Theme preference').selectOption('light');await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.getByRole('link',{name:'Projects',exact:true}).click();await expect(page.getByRole('heading',{name:'Projects with purpose'})).toBeVisible();await page.screenshot({path:'test-results/projects-light.png',fullPage:true});
 await page.getByRole('link',{name:'Reports & import'}).click();const dl=page.waitForEvent('download');await page.getByRole('link',{name:/Assignments Download/}).click();await expect((await dl).suggestedFilename()).toContain('assignments');
});
test('mobile reduced motion and 2D fallback',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/');
 await expect(page.getByRole('heading',{name:/The right people/})).toBeVisible();await page.locator('.hero-visual').getByRole('button',{name:'2D view'}).click();
 await expect(page.locator('.hero-visual svg.fallback')).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/mobile-landing.png',fullPage:true});await page.screenshot({path:'test-results/mobile-viewport.png'});await page.setViewportSize({width:820,height:1180});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.setViewportSize({width:390,height:844});
 await page.goto('/login');await page.getByLabel('Email address').fill('volunteer@demo.skillweave.test');await page.getByLabel('Password',{exact:true}).fill('WeaveDemo!2026');await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.getByRole('heading',{name:'Good to see you, Avery.'})).toBeVisible();
 await page.getByRole('button',{name:'Toggle navigation'}).click();await expect(page.getByRole('link',{name:'Skills & availability'})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('all role workspaces render without runtime errors in both themes',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 for(const role of ['coordinator','leader','volunteer','admin']){
  await page.goto('/login');await page.getByLabel('Email address').fill(role+'@demo.skillweave.test');await page.getByLabel('Password',{exact:true}).fill('WeaveDemo!2026');await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.getByRole('heading',{name:/Good to see you/})).toBeVisible();
  for(const theme of ['light','dark']){
   await page.getByLabel('Theme preference').selectOption(theme);
   for(const path of ['projects','profile','settings','organization','assignments','hours','feedback','analytics','notifications','reports',...(role==='volunteer'?[]:['tasks','volunteers']),...(['coordinator','admin'].includes(role)?['optimization','simulator','audit']:[]),...(role==='admin'?['admin']:[])]){
    await page.goto('/app/'+path);await expect(page.locator('.page-heading h1')).toBeVisible();await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
   }
  }
 }
 expect(errors).toEqual([]);
});
