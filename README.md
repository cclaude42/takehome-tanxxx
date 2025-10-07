## User Journey Dashboard

A lightweight Streamlit dashboard to explore shopper behavior from event logs.

## Installation

### Prerequisites
- **Python**: `>=3.13`
- **uv** (comprehensive Python package and environment manager )

### 1) Clone the repository
```bash
git clone https://github.com/cclaude42/takehome-tanxxx.git
cd takehome-tanxxx
```

### 2) Fetch the data
```bash
# From the repo root
curl https://s3.eu-central-1.amazonaws.com/public.prod.usetandem.ai/sessions.json > sessions.json
```

### 3) Setup with uv
```bash
# Install dependencies declared in pyproject.toml
uv sync
```

## Running the app

### Streamlit dashboard

```bash
uv run streamlit run dashboard.py
```
- Your browser should open automatically. If not, visit `http://localhost:8501`.

### Optional: quick CLI exploration

A small helper in `data_exploration.py` prints top-line stats from `sessions.json`:
```bash
uv run python data_exploration.py
```

## Approach & methodology

I started with a quick exploration of the data provided, using Python and Pandas (chosen for their simplicity when dealing with data exploration).

Having a quick look in the CLI, I identified what I wanted to target in the data and found a common user pattern : `/products -> /cart -> /checkout`.

```
Number of users: 11
Number of users with multiple sessions: 9
Number of users with single session: 2
User 0a0b0c0d-0e0f-1011-1213-141516171819 has 7 events
                       path                  css                 text              value          event_time
0  /products/headphones-xyz     .product-details       Headphones XYZ                    2025-02-06 09:25:02
1  /products/headphones-xyz     textarea.comment              Comment  Sound is mediocre 2025-02-06 09:25:08
2  /products/headphones-xyz   button.add-to-cart          Add to Cart                    2025-02-06 09:25:14
3                     /cart      button.checkout  Proceed to Checkout                    2025-02-06 09:25:18
4                 /checkout    div.error-message     Payment declined                    2025-02-06 09:25:23
5                 /checkout         button.retry                Retry                    2025-02-06 09:25:28
6                 /checkout  button.cancel-order         Cancel Order                    2025-02-06 09:25:33
User 0a0b0c0d-0e0f-1011-1213-141516171819 has 7 events
                       path                 css                 text         value          event_time
0                   /random     .random-section       Random Content               2025-02-06 11:00:03
1                   /random         #search-bar               Search       headset 2025-02-06 11:00:07
2                 /products       .product-card       Gaming Headset               2025-02-06 11:00:14
3  /products/gaming-headset    textarea.comment              Comment  Bass is deep 2025-02-06 11:00:16
4  /products/gaming-headset  button.add-to-cart          Add to Cart               2025-02-06 11:00:23
5                     /cart     button.checkout  Proceed to Checkout               2025-02-06 11:00:26
6                 /checkout  button.place-order          Place Order               2025-02-06 11:00:33
User 0a0b0c0d-0e0f-1011-1213-141516171819 has 5 events
                     path                 css                 text  value          event_time
0                       /         #search-bar               Search  mouse 2025-02-06 10:10:02
1               /products       .product-card         Gaming Mouse        2025-02-06 10:10:08
2  /products/gaming-mouse  button.add-to-cart          Add to Cart        2025-02-06 10:10:11
3                   /cart     button.checkout  Proceed to Checkout        2025-02-06 10:10:16
4                /account       button.logout               Logout        2025-02-06 10:10:22
```

Next, I made some quick visualizations using Plotly. I decided to go for something slightly more interactive, so I ditched Plotly and moved to Streamlit.

I built a simple Streamlit app (easy visualization dashboarding in Python), with three views :
- One 'user funnel' to identify the number of users going from one step to the next.
- One 'step details' view, to allow the product team to investigate user data for a specific step.
- One 'customer insights' view, to group by error type and bubble up potential issues with the site or UX.

## Insights derived from the dataset

The following errors led to no purchase from users :
- Payment declined
- Payment service was unavailable
- Payment method was unrecognized
- Item was out of stock
- User was unable to update preference (language?)
- User did not find an answer in the FAQ

I would consider investigating payment service logs, to verify this is a user issue and not on our end. I would also troubleshoot preference options, and add answers to the FAQ (here, we see order tracking and return policy are of interest to customers)

## Next steps
- Host on a URL so product teams can access it
- Support multiple files and uploads, or automate the pipeline that places session data where the app runs
- Evaluate `polars` as a performance-focused alternative to `pandas`, alternatives to streamlit if performance or app size become an issue.
