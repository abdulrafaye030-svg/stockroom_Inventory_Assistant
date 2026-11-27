# Stockroom Inventory Assistant

Stockroom is a local inventory dashboard with a conversational assistant. The interface is built with React and Vite; a small Python HTTP service connects it to the existing SQLite demo database or an optional MongoDB database.

## What the project does

- Shows product totals and counts for in-stock, low-stock, and out-of-stock items.
- Lists products with their quantity, unit, reorder point, and stock status.
- Filters the catalog by stock status and searches by product name.
- Highlights items that need a stock check. Stock bars compare quantity with each product's reorder point.
- Answers questions about stock, reordering, and customer balances in the chat panel.
- Supports follow-up prompts: for example, ask to check a product, then enter its name.
- Offers a refresh action to reload data from the connected database.
- Provides a responsive layout for desktop and smaller screens.

The **In stock** count includes every product with a positive quantity; **Low stock** is a subset of that count. A product is low when its positive stock is at or below its reorder point. A quantity of zero or below counts as out of stock.

## How it works

```text
React app (src/)
    │  GET /api/products, GET /api/health, POST /api/chat
    ▼
Python service (server.py)
    ├── chatbot.py   matches questions and formats answers
    └── database.py  reads SQLite or MongoDB
```

In development, Vite serves the React app and forwards `/api` requests to the Python service on port `8000`. In production, the Python service serves both the built React files in `dist/` and the API.

## Project files

| File | Purpose |
| --- | --- |
| `src/App.jsx` | Dashboard, product filters/search, inventory metrics, navigation, and chat state/API calls. |
| `src/inventory.js` | Product filtering, metric counts, stock-bar widths, message IDs, and API requests used by the app. |
| `src/inventory.test.js` | Vitest tests for `src/inventory.js`. |
| `tests/test_fixes.py` | Python tests for the chat, stock status, and error-message logic. |
| `src/Icon.jsx` | Reusable inline SVG icons, including the Stockroom mark. |
| `src/main.jsx` | React entry point; mounts the app and loads its styles. |
| `src/styles.css` | Dashboard, chat, responsive layout, and visual design. |
| `index.html` | HTML shell used by Vite and the production build. |
| `vite.config.js` | Vite configuration and development proxy for `/api` to `127.0.0.1:8000`. |
| `package.json` / `package-lock.json` | Frontend scripts and pinned JavaScript dependencies. |
| `server.py` | Local HTTP API, request validation, and production static-file server. |
| `auth.py` | Sign-in credential check and signed session cookies. |
| `src/LoginPage.jsx` | Sign-in form shown until the user is signed in. |
| `chatbot.py` | Supported question phrases, product/customer name matching, and terminal chatbot. |
| `database.py` | SQLite/MongoDB connections, inventory queries, balance calculations, and data errors. |
| `inventory_demo_v3.db` | SQLite demo database used by default (created with sample data on first run; not committed). |

## Requirements

- Python 3.9 or newer
- Node.js and npm

SQLite support is included with Python. MongoDB mode additionally requires PyMongo.

## Run in development

Open two PowerShell terminals in the project directory:

```powershell
Set-Location 'C:\path\to\stockroom_Inventory_Assistant'
```

In **Terminal 1**, start the Python API:

```powershell
py server.py
```

In **Terminal 2**, install the frontend dependencies (first run only) and start Vite:

```powershell
npm install
npm run dev
```

Open the Vite URL printed in Terminal 2, normally <http://localhost:5173>. Keep both terminals running while using the app. Press `Ctrl+C` in each terminal to stop its service.

## Build and run in production mode

From the project directory:

```powershell
npm install
npm run build
py server.py
```

Vite writes the production frontend to `dist/`. The Python service detects that build and serves the complete app at <http://127.0.0.1:8000>.

## Sign in

The app opens on a sign-in form. Product, customer and chat data are only returned to a signed-in session.

- **Default account:** username `rafay`, password `rafay1234`. This is used only when no credentials are configured.
- **Your own account:** set `STOCKROOM_USERNAME` and `STOCKROOM_PASSWORD` before starting the server (or in your host's environment variables).
- **Signing key:** set `STOCKROOM_SECRET` to a long random string in production. Without it the key is derived from the password, so changing the password signs everyone out.

Sessions last 12 hours and are kept in an HttpOnly cookie (marked `Secure` on Vercel or behind HTTPS). There is one account; the username is not case-sensitive, the password is.

```powershell
$env:STOCKROOM_USERNAME = 'owner'
$env:STOCKROOM_PASSWORD = 'choose-a-strong-password'
$env:STOCKROOM_SECRET = 'a-long-random-string'
py server.py
```

> **Before deploying publicly, set these variables.** Otherwise anyone can sign in with the default account above.

## Deploy online

### Vercel

Import the GitHub repository at [vercel.com/new](https://vercel.com/new) and deploy with the default settings (`vercel.json` selects Vite and `dist/`). Vercel serves the React build as static files and runs the files in `api/` as Python functions; each reuses `server.py`. Add `STOCKROOM_USERNAME`, `STOCKROOM_PASSWORD` and `STOCKROOM_SECRET` under **Settings → Environment Variables** (see [Sign in](#sign-in)). On Vercel the SQLite demo database is created in the temporary folder, so it is reset whenever a function restarts.

### Docker (Render and other hosts)

The included `Dockerfile` builds the React app and runs `server.py` on the port the host provides (`PORT`, default `8000`). To deploy on [Render](https://render.com):

1. Create a **Web Service** and connect this GitHub repository.
2. Choose the **Docker** language/runtime and the **Free** instance type.
3. Deploy. Render builds the image and gives the app a public `onrender.com` URL.

The SQLite demo database is recreated with sample data each time the service starts. To use MongoDB instead, add `MONGODB_URI` and `MONGODB_DB` as environment variables, add `pymongo` to the image, and start the server with `--mongo`.

## Run the tests

From the project directory:

```powershell
npm test                         # frontend tests (Vitest)
py -m unittest discover tests    # Python tests
```

The Python tests use an in-memory copy of the demo database, so they never change the demo database file.

## Use MongoDB instead of the demo database

Set the connection values in the PowerShell window that will run the Python service:

```powershell
$env:MONGODB_URI = 'mongodb://localhost:27017'
$env:MONGODB_DB = 'your_database_name'
py -m pip install pymongo
py server.py --mongo
```

Start Vite in the second terminal as described above, or build the frontend and open the Python service URL. The MongoDB collection and field mappings are configured near the top of `database.py`:

- Collections: `products`, `customers`, and `orders` (used for invoices).
- Product fields: `name`, `stock`, `unit`, and `reorder_level`.
- Customer fields: `_id` and `name`.
- Order fields: `customer_id`, `total`, and `amount_paid`.

Adjust those mappings if the MongoDB schema uses different names.

## Demo database model

The SQLite demo uses three tables:

| Table | Fields used |
| --- | --- |
| `products` | `name`, `stock`, `unit`, `reorder_level` |
| `customers` | `id`, `name` |
| `invoices` | `customer_id`, `total`, `paid` |

`database.py` creates the demo tables and sample rows if the database file does not yet contain a `products` table.

## API reference

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Confirms the service is running and reports the active data source. |
| `POST` | `/api/login` | Accepts `{"username", "password"}`; on success sets the session cookie. Wrong details return `401`. |
| `POST` | `/api/logout` | Clears the session cookie. |
| `GET` | `/api/session` | Returns `{"authenticated", "user"}` for the current cookie. |
| `GET` | `/api/customers` | Returns each customer's billed, paid and remaining amounts, largest balance first. |
| `GET` | `/api/products` | Returns product names, quantities, units, reorder levels, and calculated statuses. |
| `POST` | `/api/chat` | Accepts a JSON chat message and returns an answer plus optional follow-up state. |

`/api/customers`, `/api/products` and `/api/chat` require a signed-in session and return `401` without one.

Example chat request:

```json
{
  "message": "check product",
  "waitingFor": null
}
```

Example response:

```json
{
  "answer": "Which product? Type its name.",
  "waitingFor": "product"
}
```

The next request can send the product name with `"waitingFor": "product"`. Customer balance follow-ups use `"waitingFor": "balance"`.

## Example questions

- `available products`
- `low stock products`
- `out of stock`
- `stock of Sugar`
- `customer dues`
- `how much does Ali owe?`
- `konsa saman kam hai?`
- `Ali ka udhaar kitna hai?`
- `help`

The chat uses the phrase matcher in `chatbot.py`; it is not a general-purpose AI model. Add or edit supported phrases there.

The same chatbot logic can also run in a terminal:

```powershell
py chatbot.py
```

For MongoDB, set the same environment variables described above and run `py chatbot.py --mongo`.

## Configuration notes

- By default, `server.py` listens only on `127.0.0.1:8000`.
- Change the Python server address/port with `py server.py --host 127.0.0.1 --port 8000`.
- If you change the development API port, update the target in `vite.config.js` to match.
- Do not commit MongoDB credentials; set them in the shell environment instead.

## Troubleshooting

- **The dashboard cannot load data:** make sure `py server.py` is running and the browser is using the Vite URL (`http://localhost:5173`) in development.
- **Port 8000 is already in use:** choose another Python port and update the Vite proxy target in `vite.config.js`.
- **MongoDB mode reports a missing driver:** run `py -m pip install pymongo`.
- **MongoDB reports missing fields or collections:** check the mappings in `database.py` against the database schema.
- **The Python server says the React build is missing:** use `npm run dev` for development or run `npm run build` before starting production mode.
