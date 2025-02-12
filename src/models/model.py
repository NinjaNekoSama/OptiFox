from dataclasses import dataclass
from typing import Optional

from interpret.glassbox import ExplainableBoostingRegressor, RegressionTree
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)

# from sklearn.inspection import permutation_importance
from sklearn.feature_selection import RFE
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from ..features.mimic_iv.feature_preprocessor import (
    BaseFeaturePreprocessor,
    GbmFeaturePreprocessor,
)


@dataclass
class RFEProps:
    n_features_to_select: int
    step: int


class IcuBaseEstimator(BaseEstimator):
    def __init__(self, estimator: BaseEstimator, rfe_props: Optional[RFEProps]):
        super().__init__()
        self.estimator = estimator
        self.pipeline = None
        self.rfe_props = rfe_props
        if self.rfe_props is not None:
            self.rfe = RFE(
                estimator=self.estimator,
                n_features_to_select=self.rfe_props.n_features_to_select,
                step=self.rfe_props.step,
            )
        # TODO generalize kwargs

    def __str__(self) -> str:
        # return name of the estimator class
        return self.estimator.__class__.__name__

    def __repr__(self):
        if self.pipeline is None:
            return self.estimator.__repr__()
        else:
            return self.pipeline.__repr__()

    def _build_pipeline(self, **kwargs):
        if self.rfe_props is not None:
            steps = [
                ("preprocess", BaseFeaturePreprocessor()),
                ("rfe", self.rfe),
                ("model", self.estimator),
            ]
        else:
            steps = [
                ("preprocess", BaseFeaturePreprocessor()),
                ("model", self.estimator),
            ]
        return Pipeline(steps=steps)

    # pylint: disable=missing-function-docstring,unused-argument
    def fit(self, X, y=None, **fit_params):
        self.pipeline = self._build_pipeline(X=X, **fit_params)
        self.pipeline = self.pipeline.fit(X, y=y, **fit_params)
        return self

    # pylint: disable=missing-function-docstring,unused-argument
    def predict(self, X, **predict_params):
        check_is_fitted(self, ["pipeline"])
        return self.pipeline.predict(X, **predict_params)  # type: ignore


class IcuBaseClassifier(IcuBaseEstimator, ClassifierMixin):
    pass


class IcuBaseRegressor(IcuBaseEstimator, RegressorMixin):
    pass


class IcuRFClassifier(IcuBaseClassifier):
    def __init__(self, rfe_props: RFEProps, **kwargs):
        super().__init__(RandomForestClassifier(**kwargs), rfe_props)


class IcuRFRegressor(IcuBaseRegressor):
    def __init__(self, rfe_props: RFEProps, **kwargs):
        super().__init__(RandomForestRegressor(**kwargs), rfe_props)


class IcuLogRegClassifier(IcuBaseClassifier):
    def __init__(self, rfe_props: RFEProps, **kwargs):
        super().__init__(LogisticRegression(**kwargs), rfe_props, **kwargs)


class IcuLinRegRegressor(IcuBaseRegressor):
    def __init__(self, rfe_props: RFEProps, **kwargs):
        super().__init__(LinearRegression(**kwargs), rfe_props)


# TODO separate preprocessing from estimator
class IcuLGBMEstimator(IcuBaseEstimator):
    def __init__(self, estimator: BaseEstimator, **kwargs):
        super().__init__(estimator=estimator.set_params(**kwargs), rfe_props=None)

    def _build_pipeline(self, **kwargs):
        # TODO has native support for both missing and categorical values

        # TODO this is quite hacky
        X = kwargs["X"]
        feature_preprocessor = GbmFeaturePreprocessor()
        feature_preprocessor._build_transformer(X=X)
        # GBM comes with categorical support. API is different depending on scikit-learn version
        # TODO Fix this. for some reason the columntransformer removes the feature labels
        # so we can't use the feature names but the indices instead
        # get version
        # scikit_version = sklearn.__version__
        # if version >= 1.2, use native categorical support
        # if scikit_version >= "1.2":
        # cat_features = feature_preprocessor.categorical_features
        # if version < 1.2, use ordinal encoding
        # else:
        num_numerical_features = len(feature_preprocessor.numerical_features)
        num_cat_featuers = len(feature_preprocessor.categorical_features)
        categorical_mask = [False] * num_numerical_features + [True] * num_cat_featuers
        if any(categorical_mask):
            self.estimator = self.estimator.set_params(categorical_features=categorical_mask)
        return Pipeline(
            steps=[
                ("preprocess", feature_preprocessor),
                ("model", self.estimator),
            ]
        )


class IcuLGBMClassifier(IcuLGBMEstimator, ClassifierMixin):
    def __init__(self, **kwargs):
        super().__init__(estimator=HistGradientBoostingClassifier(**kwargs))


class IcuLGBMRegressor(IcuLGBMEstimator, RegressorMixin):
    def __init__(self, **kwargs):
        super().__init__(estimator=HistGradientBoostingRegressor(**kwargs))


class IcuXLGBMRegressor(ExplainableBoostingRegressor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class IcuXTreeRegressor(RegressionTree):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
