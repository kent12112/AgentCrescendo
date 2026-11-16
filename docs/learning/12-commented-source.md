# Reading the commented source

The maintained source, tests, scripts, and supported configuration contain plain-English
comments translating the adjacent code. Comments describe what an operation does;
the implementation, tests, and observed runtime results remain the evidence for behavior.

## How the annotations work

- Python comments translate the following statement or argument. Structural closing
  delimiters and docstrings do not need a second narration. Existing explanatory
  comments and executable strings are preserved.
- Embedded programs and prompts use `string line N` notes outside the literal,
  counting from immediately after the opening triple quote. Keeping notes outside
  preserves the exact text sent to models, browsers, or remote desktops.
- TypeScript comments explain declarations, conditions, state updates, and requests.
  `JSX line N` refers to line N of the JSX tree below, including blank lines.
  These notes stay outside the tree so they do not render in the interface.
- CSS, TOML, YAML, INI, and migration templates use their supported comment syntax.
- JSON cannot contain comments. The application JSON files are explained line by
  line below. Lockfiles, dependencies, build output, private environment files,
  generated `next-env.d.ts`, and historical reading copies are excluded.

## Read one execution path at a time

For persisted drafts, start at `apps/web/app/page.tsx`, then read
`features/drafts/workspace.tsx`, `use-drafts.ts`, `draft-list.tsx`, the server proxy
under `app/api/`, and the API's `main.py`, `auth.py`, `routes/runs.py`, `schemas.py`,
`models.py`, and `database.py`. Open `services/api/tests/test_runs.py` alongside
this path to see how validation, persistence, and deletion are checked.

For the agent, start at `scripts/e2b_visual_research_demo.py`, then read
`vision_loop.py`, `vision.py`, security `policy.py`, `e2b_desktop.py`, and
`browser_bootstrap.py`. Read `live_view.py` for the user's viewing path. The
screenshot sent to the model and the user's live stream are separate channels.
Runtime tests replace provider dependencies with fakes; they do not prove a real
provider connection or network boundary.

The [codebase guide](../codebase.md) maps file responsibilities and common changes.

## Understand these distinctions as you read

Python type hints describe expected values; Pydantic performs runtime request
validation. SQL CHECK constraints independently reject invalid database rows.
`bool` subclasses `int` in Python, so exact `type(value) is int` checks deliberately
reject booleans for action counts. SQLAlchemy sessions group work; a successful
`commit()` makes database writes durable. Closing a session rolls back uncommitted
work but does not undo an already committed transaction.

The model proposes an action; authorization decides whether it may execute.
A tool description, model reason, or page instruction cannot expand the task
allowlist. Reporting a successful SDK call does not prove the intended visual
result: inspect the next screenshot. Application URL checks and provider network
controls have different responsibilities; the remaining live networking checks
are still listed in status.

`with` delegates lifetime behavior to a context manager. `finally` executes on
normal returns and exceptions, but cannot guarantee cleanup after process death.
`await` lets other async work run while waiting; it does not make operations
parallel unless multiple tasks are scheduled. React state setters schedule a new
render; the current render's variables do not update in place. Functional setters
such as `setRuns(previous => ...)` receive the latest state.

## Practice explaining a line

For each function, predict its inputs, output, side effects, and failure path.
Trace where a value came from and whether it is trusted. Then choose a matching
test, predict the outcome of changing one condition, and run that test. Use a
throwaway edit or branch for experiments and restore intentional behavior.

A useful checkpoint is explaining why the authorization call must precede scroll,
why a repeated deletion returns 404, why fetch needs response.ok, and why a
provider timeout does not establish whether a remote effect already happened.
Being able to reason about those consequences matters more than memorizing syntax.

## Strict JSON configuration, line by line

Line numbers below refer to the unchanged JSON files. Opening/closing braces and
brackets group objects and arrays; commas separate entries. A quoted object key
names a setting. JSON values are data, not executed JavaScript.

### `apps/web/package.json`

| Line | Source | Explanation |
| --- | --- | --- |
| 1 | `{` | Open an object (named fields) or array (ordered values). |
| 2 | `"name": "agent-crescendo-web",` | The npm package name for the local dashboard. |
| 3 | `"version": "0.1.0",` | The dashboard package version. |
| 4 | `"private": true,` | Prevent accidental npm publication of this workspace package. |
| 5 | `"scripts": {` | Define commands invoked by npm run. |
| 6 | `"dev": "next dev --webpack --hostname 127.0.0.1",` | Start the local Next.js development server using Webpack, bound to loopback. |
| 7 | `"build": "next build --webpack",` | Create the production build using Webpack; this does not publish the app. |
| 8 | `"start": "next start --hostname 127.0.0.1",` | Serve an existing production build on loopback. |
| 9 | `"typecheck": "tsc --noEmit"` | Run TypeScript checking without emitting JavaScript. |
| 10 | `},` | Close the current object/array; a following comma allows another sibling entry. |
| 11 | `"dependencies": {` | Packages required by the running dashboard. |
| 12 | `"next": "16.4.6",` | The pinned Next.js framework version for routing, rendering, and builds. |
| 13 | `"react": "19.3.1",` | The pinned React component/state implementation. |
| 14 | `"react-dom": "19.3.1"` | The pinned React DOM rendering implementation. |
| 15 | `},` | Close the current object/array; a following comma allows another sibling entry. |
| 16 | `"devDependencies": {` | Build-time and type-checking dependencies. |
| 17 | `"@tailwindcss/postcss": "4.1.18",` | The Tailwind plugin used by the PostCSS build step. |
| 18 | `"tailwindcss": "4.1.18",` | The pinned Tailwind CSS framework. |
| 19 | `"typescript": "5.9.3",` | The pinned TypeScript compiler. |
| 20 | `"@types/node": "^22.0.0",` | Node.js type declarations for server/build APIs; caret permits compatible updates. |
| 21 | `"@types/react": "^19.0.0",` | React type declarations; these are compile-time data, not the runtime implementation. |
| 22 | `"@types/react-dom": "^19.0.0"` | React DOM type declarations. |
| 23 | `}` | Close the current object/array; a following comma allows another sibling entry. |
| 24 | `}` | Close the current object/array; a following comma allows another sibling entry. |

### `apps/web/tsconfig.json`

| Line | Source | Explanation |
| --- | --- | --- |
| 1 | `{` | Open an object (named fields) or array (ordered values). |
| 2 | `"compilerOptions": {` | Group settings controlling TypeScript parsing, checking, and output. |
| 3 | `"target": "ES2017",` | Check/emit against the ES2017 language target; Next.js handles the final build pipeline. |
| 4 | `"lib": [` | List the built-in API type declaration libraries available while checking. |
| 5 | `"dom",` | Browser DOM API types, such as document, fetch, and HTMLElement. |
| 6 | `"dom.iterable",` | Iterable browser collection types. |
| 7 | `"esnext"` | Latest available standard-library API types; types do not supply runtime polyfills. |
| 8 | `],` | Close the current object/array; a following comma allows another sibling entry. |
| 9 | `"allowJs": false,` | Do not include ordinary JavaScript files as checked TypeScript inputs through this option. |
| 10 | `"skipLibCheck": true,` | Skip checking dependency declaration-file internals; application usage is still checked. |
| 11 | `"strict": true,` | Enable the strict family of TypeScript checks, including null checking. |
| 12 | `"noEmit": true,` | Type-check without writing JavaScript output; Next.js owns the build. |
| 13 | `"esModuleInterop": true,` | Allow common interoperability between CommonJS dependencies and ES module imports. |
| 14 | `"module": "esnext",` | Keep modern ES module syntax for the bundler. |
| 15 | `"moduleResolution": "bundler",` | Resolve imports using rules appropriate to bundler-managed modules. |
| 16 | `"resolveJsonModule": true,` | Allow typed imports of JSON modules. |
| 17 | `"isolatedModules": true,` | Require each file to be independently transpilable by tools such as the Next.js compiler. |
| 18 | `"jsx": "react-jsx",` | Use the automatic React JSX runtime when JSX is transformed. |
| 19 | `"incremental": true,` | Cache type-checking information to speed up subsequent checks. |
| 20 | `"plugins": [` | Configure editor/compiler integrations. |
| 21 | `{` | Open an object (named fields) or array (ordered values). |
| 22 | `"name": "next"` | Select the Next.js TypeScript plugin. |
| 23 | `}` | Close the current object/array; a following comma allows another sibling entry. |
| 24 | `]` | Close the current object/array; a following comma allows another sibling entry. |
| 25 | `},` | Close the current object/array; a following comma allows another sibling entry. |
| 26 | `"include": [` | Include these application and generated declaration paths in type checking. |
| 27 | `"next-env.d.ts",` | Framework-generated ambient declarations; Next.js regenerates this file. |
| 28 | `"**/*.ts",` | All TypeScript source/declaration files below this directory. |
| 29 | `"**/*.tsx",` | All TypeScript files containing JSX below this directory. |
| 30 | `".next/types/**/*.ts",` | Generated framework routing/type declarations. |
| 31 | `".next/dev/types/**/*.ts"` | Development-mode generated framework declarations. |
| 32 | `],` | Close the current object/array; a following comma allows another sibling entry. |
| 33 | `"exclude": [` | Exclude these paths from initial file discovery. |
| 34 | `"node_modules"` | Installed external dependencies; their source is not part of this annotation task. |
| 35 | `]` | Close the current object/array; a following comma allows another sibling entry. |
| 36 | `}` | Close the current object/array; a following comma allows another sibling entry. |

