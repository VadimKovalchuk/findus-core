import pytest

from tests.tests_edge.test_normalization import UNIFORM_DISTRIBUTION_DATA
from ticker.models import Scope, Ticker, FinvizFundamental


@pytest.fixture
def algo_scope():
    scope = Scope.objects.create(name='scope')
    for symbol in UNIFORM_DISTRIBUTION_DATA:
        # logger.debug(symbol)
        tkr = Ticker.objects.create(symbol=symbol)
        tkr.save()
        scope.tickers.add(tkr)
        finviz_slice: FinvizFundamental = FinvizFundamental.objects.create(
            ticker=tkr,
            price_earnings=UNIFORM_DISTRIBUTION_DATA[symbol],
            price_sales=UNIFORM_DISTRIBUTION_DATA[symbol] * 2
        )
        finviz_slice.save()
        # logger.debug([finviz_slice.price_earnings, finviz_slice.price_sales])
    scope.save()
    yield scope
