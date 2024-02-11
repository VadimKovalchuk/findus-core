from algo.algorithm.generic import Algorithm, Metric
from ticker.models import Scope


class FinvizAlgorithm(Algorithm):
    name = 'finviz_initial_algorithm'
    scope = Scope.objects.get(name="SP500")
    default_metrics = [
        Metric(
            name='price_earnings',
            weight=0.2,
            normalization_method='minmax_inverted',
            target_model='FinvizFundamental',
            target_field='price_earnings',
        ),
        Metric(
            name='price_earnings_growth',
            weight=0.15,
            normalization_method='minmax_inverted',
            target_model='FinvizFundamental',
            target_field='price_earnings_growth',
        ),
        Metric(
            name='price_sales',
            weight=0.1,
            normalization_method='minmax_inverted',
            target_model='FinvizFundamental',
            target_field='price_sales',
        ),
        Metric(
            name='debt_equity',
            weight=0.1,
            normalization_method='minmax_inverted',
            target_model='FinvizFundamental',
            target_field='debt_equity',
        ),
        Metric(
            name='current_ratio',
            weight=0.1,
            normalization_method='minmax',
            target_model='FinvizFundamental',
            target_field='current_ratio',
        ),
        Metric(
            name='return_equity',
            weight=0.1,
            normalization_method='minmax',
            target_model='FinvizFundamental',
            target_field='return_equity',
        ),
        Metric(
            name='return_asset',
            weight=0.1,
            normalization_method='minmax',
            target_model='FinvizFundamental',
            target_field='return_asset',
        ),
        Metric(
            name='profit_margin',
            weight=0.15,
            normalization_method='minmax',
            target_model='FinvizFundamental',
            target_field='profit_margin',
        ),
    ]
