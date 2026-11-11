# Stock Price vs. Company Growth

Type a ticker and see how a stock's price has moved compared with the company's
revenue, net income, or EPS. Both lines are indexed to 100 at the first report
date, so you can tell at a glance whether the stock has run ahead of the
business or fallen behind it.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Hosted free on [Streamlit Community Cloud](https://share.streamlit.io): point it
at this repo with `app.py` as the main file.

Data: Yahoo Finance via `yfinance`. For education only, not investment advice.
