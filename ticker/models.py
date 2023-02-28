from django.db import models


HISTORY_LIMIT_DATE = '2017-01-01'

class AbstractTicker(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    symbol = models.CharField(max_length=6)

    class Meta:
        abstract = True

    def __str__(self):
        return self.symbol


class Ticker(AbstractTicker):
    company = models.CharField(max_length=100, null=True)

    def get_price_by_date(self, date: str):
        return self.price_set.filter(date=date)

    def add_price(self, price_data_list: list) -> bool:
        date, _open, high, low, close, volume = price_data_list
        if self.get_price_by_date(date=date):
            # TODO: Generate corresponding schedule
            # logger.debug(f'{ticker_name} price for {date} already exists')
            return False
        else:
            Price.objects.create(ticker=self, date=date, open=_open, high=high, low=low, close=close, volume=volume)
            return True

    def get_dividend_by_date(self, date: str):
        return self.dividend_set.filter(date=date)

    def add_dividend(self, dividend_data_list: list) -> bool:
        date, size = dividend_data_list
        if self.get_dividend_by_date(date=date):
            # TODO: Generate corresponding schedule
            # logger.debug(f'{ticker_name} dividend for {date} already exists')
            return False
        else:
            Dividend.objects.create(ticker=self, date=date, size=size)
            return True


class Price(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    date = models.DateTimeField()
    open = models.FloatField(null=True)
    high = models.FloatField(null=True)
    low = models.FloatField(null=True)
    close = models.FloatField(null=True)
    volume = models.FloatField(null=True)


class Dividend(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    date = models.DateTimeField()
    size = models.FloatField()


class FinvizFundamental(models.Model):
    id = models.AutoField(primary_key=True, help_text='Internal ID')
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True, help_text='Data slice date')

    market_cap = models.FloatField(null=True, help_text='Market capitalisation')
    income = models.FloatField(null=True)
    sales = models.FloatField(null=True, help_text='Revenue')
    book_share = models.FloatField(null=True, help_text='Book/share')
    cash_share = models.FloatField(null=True, help_text='Cash/share')
    dividend = models.FloatField(null=True, help_text='Actual dividend value')
    dividend_percent = models.FloatField(null=True, help_text='Relative dividend value')
    recommendation = models.FloatField(null=True, help_text='Analysts mean recommendation. 1-Buy, 5-sell')

    price_earnings = models.FloatField(null=True, help_text='P/E')
    price_earnings_forward = models.FloatField(null=True, help_text='Forward P/E')
    price_earnings_growth = models.FloatField(null=True, help_text='Price to earnings growth')
    price_sales = models.FloatField(null=True, help_text='Price to sales')
    price_book = models.FloatField(null=True, help_text='Price to book')
    price_cash = models.FloatField(null=True, help_text='Price to cash per share')
    price_free_cash = models.FloatField(null=True, help_text='Price to free cash flow per share')
    quick_ratio = models.FloatField(null=True, help_text='Quick ratio')
    current_ratio = models.FloatField(null=True, help_text='Current ratio')
    debt_equity = models.FloatField(null=True, help_text='Debt to equity')
    lt_debt_equity = models.FloatField(null=True, help_text='Long term debt to equity')

    eps_ttm = models.FloatField(null=True, help_text='EPS TTM')
    eps_next_y = models.FloatField(null=True, help_text='EPS next year')
    eps_next_q = models.FloatField(null=True, help_text='EPS next quarter')
    eps_this_y = models.FloatField(null=True, help_text='EPS this year')
    eps_next_5y = models.FloatField(null=True, help_text='EPS next 5 years')
    eps_past_5y = models.FloatField(null=True, help_text='EPS past 5 years')
    sales_past_5y = models.FloatField(null=True, help_text='Annual sales price past 5 years')
    sales_qq = models.FloatField(null=True, help_text='Quarterly relative sales growth')
    eps_qq = models.FloatField(null=True, help_text='Quarterly relative EPS growth')

    return_asset = models.FloatField(null=True, help_text='Return on asset')
    return_equity = models.FloatField(null=True, help_text='Return on equity')
    return_invest = models.FloatField(null=True, help_text='Return on investment')
    gross_margin = models.FloatField(null=True, help_text='Gross margin')
    oper_margin = models.FloatField(null=True, help_text='Operational margin')
    profit_margin = models.FloatField(null=True, help_text='Profit margin')
    payout_ratio = models.FloatField(null=True, help_text='Dividend payout ratio')

    target_price = models.FloatField(null=True, help_text='Interpolated theoretical worth price')
    beta = models.FloatField(null=True, help_text='Market relative beta')
    sma20 = models.FloatField(null=True, help_text='Distance from 20-Day Simple Moving Average')
    sma50 = models.FloatField(null=True, help_text='Distance from 50-Day Simple Moving Average')
    sma200 = models.FloatField(null=True, help_text='Distance from 200-Day Simple Moving Average')
