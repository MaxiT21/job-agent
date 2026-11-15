import { expect, test } from "@playwright/test";

test("a visitor replays the strong-match run end to end", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/no ai is called/i)).toBeVisible();

  await page.getByRole("link", { name: /strong match/i }).click();
  await expect(page.getByRole("button", { name: /approve and create/i })).toBeVisible({ timeout: 15_000 });

  // the evidence behind a requirement is the profile's own text
  const chip = page.getByRole("table", { name: "Requirements" }).getByRole("button").first();
  await chip.hover();
  await expect(page.getByRole("tooltip")).not.toHaveText(/not in the current profile/i);

  await page.getByRole("button", { name: /approve and create/i }).click();
  const download = page.getByRole("link", { name: /download cv/i });
  await expect(download).toBeVisible({ timeout: 15_000 });
  const res = await page.request.get((await download.getAttribute("href"))!);
  expect(res.status()).toBe(200);
});

test("the demo embeds only in the portfolio", async ({ request }) => {
  const res = await request.get("/");
  expect(res.headers()["content-security-policy"]).toContain(
    "frame-ancestors 'self' https://maximotorassa.vercel.app",
  );
});
