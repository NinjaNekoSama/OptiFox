# ICU Length of Stay Prediction
Context:
The (remaining) length-of-stay of patients in the intensive care unit is of great importance for planning and management of ICU resources. Currently this is not done in a data-driven way. We want to predict the length of stay for new, incoming ICU patients at some point after their surgery (to be determined) and the remaining length of stay for patients already in the ICU.
Tasks:
- [ ] Define prediction time points for new and existing patients
    - [ ] $n$ hours after surgery
    - [x] $24$ hours after ICU admisson
    - [ ] periodically each $n$ hours/days for remaining LOS
- [ ] Define prediction targets for new and existing patients
    - [ ] Binary: short/long stay
    - [x] Regression: remaining length of stay
- [ ] Define features for new and existing patients
    - basic hospital features
    - ICU chartevent subsets
        - [x] respiratory signals
        - [x] routine vital signs
        - [x] alarms
        - [ ] many others
    - ICU labevents subsets
        - [ ] tbd
    - differentiate between available features at different points in time
- [x] Define evaluation metrics
    - Mean Absolute Error (MAE)
    - Mean Squared Error (MSE)
    - Root Mean Squared Error (RMSE)
    - R2 Score

- [x] Define baseline models
    - Base Models: Linear Regression, Decision Tree
    - Ensemble Methods: Random Forest, (Extreme) Gradient Boosting
- [ ] Define evaluation procedure
- [x] Implement baseline models
    - [ ] Decision Tree
    - [ ] XGBoost
- [ ] Implement evaluation procedure
    - [ ] Nested cross validation
    - [ ] hyperparameter tuning
    - [ ] Experiment tracking using e.g. MLflow
- [x] Evaluate baseline models
- [ ] Define and implement advanced models
- [ ] Evaluate advanced models
- [ ] Write report
- [ ] Present results

## Features
MIMIC-IV subsets used[^1]:


### Hosp Module
- `admissions`
    - admission type
    - admission location
    - admission time
        - day of week
        - hour of day
        - month
        - season
    - ED length of stay
    - _insurance_
    - _language_
    - _marital status_
    - _race_
- `patients`
    - gender
    - age
        - calculated from anchor_age and admission time
    - age group

- `services`
    - surgery stays only
    - surgery type (service)
- `omr`
    - BMI
    - height
    - weight
    - Blood Pressure
    - date of last measurement


### ICU Module
- `icustays`
    - ICU intime
        - hours after surgery
- `d_items`
    - names and especially categories for different items in `chartevents` (and others)
- `chartevents`
    - using min/max/mean/std right now.
    - respiratory signals
        - respiratory rate
        - o2 saturation
        - o2 flow
    - routine vital signs
        - blood pressure (systolic, diastolic, mean)
            - non invasive
            - arterial
        - temperature
    - alarms
        - _number of [high/low] alarms during stay_
        - blood pressure
            - arterial
            - central venous
            - non invasive
        - heart rate
        - o2 saturation
        - SpO2 desaturation
        - respiratory rate


[^1]: features in italics may not be available in UKA dataset

## Models
- Linear Regression
- Random Forest
- Gradient Boosting

Note: No hyperparameter tuning was done yet.


## Evaluation
### Metrics
- Mean Absolute Error (MAE)
- Mean Squared Error (MSE)
- Root Mean Squared Error (RMSE)
- R2 Score
- Explained Variance Score

### Procedure
- 5-fold cross validation
- different feature subsets:
    - Base: using only hospital data + `icustays`
    - Vitals: Base + routine vital signs from `chartevents`
    - Respiratory: Base + respiratory signals from `chartevents`
    - Alarms: Base + alarms from `chartevents`
    - All possible combinations of the above
- equal preprocessing for all experiments *by model type*
    - GB supports categorical features natively and does not need one-hot encoding
    - while GB supports missing values natively and does not need imputation, we still impute missing values for all models to ensure equal preprocessing
    - imputation: mean for numerical features, most frequent for categorical features


## Results
### Base Hospital Features vs. All Features
Model: Random Forest

Note: this was done using a 80/10/10 split instead of cross validation, results showing predictions on validation set.
![All Features](./figures/reg_base_vs_all.png)
### Feature Tuples Comparison
Models: Random Forest, Gradient Boosting (LightGBM / `HistGradientBoostingRegressor`) - Linear Regressor did not converge
Note: no hyperparameter tuning was done yet.
![Comparison of different feature subsets](./figures/los_pred_chartevent_subsets.png)

Notable Conclusions:
- Number of alarms seems to be highly predictive of ICU LOS, all experiments including it perform significantly better
- Adding respiratory and vital signs features on top does not improve performance as of right now.
    - but combining both does improve performance in models without alarms
    - so the feature importance may just be lower and/or the features may need different processing
