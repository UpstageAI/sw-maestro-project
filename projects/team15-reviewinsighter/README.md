# sv

Everything you need to build a Svelte project, powered by [`sv`](https://github.com/sveltejs/cli).

## Creating a project

If you're seeing this, you've probably already done this step. Congrats!

```sh
# create a new project
npx sv create my-app
```

To recreate this project with the same configuration:

```sh
# recreate this project
bun x sv@0.15.2 create --template minimal --types ts --add tailwindcss="plugins:none" --install bun review-insighter
```

## Developing

Once you've created a project and installed dependencies with `npm install` (or `pnpm install` or `yarn`), start a development server:

```sh
npm run dev

# or start the server and open the app in a new browser tab
npm run dev -- --open
```

## Building

To create a production version of your app:

```sh
npm run build
```

You can preview the production build with `npm run preview`.

> To deploy your app, you may need to install an [adapter](https://svelte.dev/docs/kit/adapters) for your target environment.

## Cloudflare Workers

This project is configured for Cloudflare Workers with `@sveltejs/adapter-cloudflare` and `wrangler`.

Copy the environment example for local development:

```sh
cp .env.example .env
```

Set your local Upstage key in `.env`:

```txt
UPSTAGE_API_KEY=your_upstage_api_key
```

For Cloudflare Workers, store the API key as a secret:

```sh
pnpm wrangler secret put UPSTAGE_API_KEY
```

Preview the Worker locally:

```sh
pnpm workers:preview
```

Deploy to Cloudflare Workers:

```sh
pnpm deploy
```

The Worker is configured to use only this custom domain:

```txt
review-insighter.jiyu.land
```
