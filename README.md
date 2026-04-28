# financial-calculator

Suppose I want to perform a monte carlo analysis of an S&P 500 investment. There will be an initial purchase and after that no purchases or withdrawals. I have daily closing prices for 30 years. I'm going to randomly pick the first of each month, so I'll have 360 price points. I expect the price difference (as a percentage) between consecutive months will follow a standard distribution.
For the monte carlo analysis I want to see how the value of a the investment will change over time. For each month in the analysis I want to pick, or perhaps interpolate, a percent change for that month. What are my options?
