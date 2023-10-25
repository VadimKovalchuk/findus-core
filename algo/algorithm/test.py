from algo.algorithm.generic import Algorithm, Metric
from ticker.models import FinvizFundamental


class TestAlgorithm(Algorithm):
    name = 'test_algorithm'
    default_metrics = [
        Metric(
            name='price_earnings',
            weight=0.6,
            normalization_method='minmax',
            target_model='FinvizFundamental',
            target_field='price_earnings',
        ),
        Metric(
            name='price_sales',
            weight=0.4,
            normalization_method='minmax',
            target_model='FinvizFundamental',
            target_field='price_sales',
        ),
    ]

