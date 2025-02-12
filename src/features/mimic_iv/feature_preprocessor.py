from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted


class BaseFeaturePreprocessor(BaseEstimator, TransformerMixin):
    """Preprocess the dataset features."""

    def __init__(self, numerical_features=None, categorical_features=None, ordinal_features=None):
        self.numerical_features = numerical_features
        self.categorical_features = categorical_features
        self.ordinal_features = ordinal_features
        self.transformer_ = None

    def _build_transformer(self, X):
        # determine categorical and numerical features if not provided
        if self.numerical_features is None:
            self.numerical_features = X.select_dtypes(include=["number"]).columns.tolist()
        if self.categorical_features is None:
            self.categorical_features = X.select_dtypes(include=["category"]).columns.tolist()
            # TODO: non-categorical features are not used at all right now!

        transform_numerical = self.get_numerical_pipeline()

        transform_categorical = self.get_categorical_pipeline()
        # TODO add trafo for ordinal features, e.g. days of week

        transformer = ColumnTransformer(
            transformers=[
                ("numerical", transform_numerical, self.numerical_features),
                ("categorical", transform_categorical, self.categorical_features),
            ],
            remainder="drop",
            verbose_feature_names_out=False,
        )

        return transformer

    def get_categorical_pipeline(self):
        return Pipeline(
            steps=[
                # TODO fix imputation - does not seem to work with e.g. strings
                (
                    "impute",
                    SimpleImputer(strategy="most_frequent"),
                ),  # TODO add indicator for missing values
                ("encode", OneHotEncoder(handle_unknown="ignore", max_categories=255 - 2)),
                # TODO handle this better, e.g. by stratifying the data
            ]
        )

    def get_numerical_pipeline(self):
        return Pipeline(
            steps=[
                ("impute", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )

    # pylint: disable=missing-function-docstring
    def fit(self, X, y=None):
        self.transformer_ = self._build_transformer(X)
        self.transformer_ = self.transformer_.fit(X, y=y)
        return self

    # pylint: disable=missing-function-docstring
    def transform(self, X):
        check_is_fitted(self, ["transformer_"])
        return self.transformer_.transform(X)

    def get_feature_names_out(self, **kwargs):
        return self.transformer_.get_feature_names_out(**kwargs)


class GbmFeaturePreprocessor(BaseFeaturePreprocessor):
    """Preprocess the dataset features."""

    def get_numerical_pipeline(self):
        return Pipeline(
            steps=[
                # TODO GBM does not need imputation, but we keep it for comparability for now
                ("impute", SimpleImputer(strategy="median")),
                # ("impute", SimpleImputer(strategy="constant", fill_value=0)),
                ("scaler", StandardScaler()),
            ]
        )

    def get_categorical_pipeline(self):
        # GBM supports categorical features natively, so we do not need to one-hot-encode them,
        # but ordinal encoding should be used to preserve [0, n_unique_categories -1] values

        return Pipeline(
            steps=[
                # TODO GBM does not need imputation, but we keep it for comparability for now
                ("impute", SimpleImputer(strategy="most_frequent")),
                (
                    "encode",
                    OrdinalEncoder(
                        handle_unknown="use_encoded_value",
                        unknown_value=-1,
                        max_categories=255 - 2,
                    ),
                ),
            ]
        )
