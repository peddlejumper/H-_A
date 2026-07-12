#!/usr/bin/env python3
"""Assemble the final hsharpmyl.hto file."""

# Read the three source files
with open('bootstrap/hsharpmyl.hto', 'r') as f:
    hsharpmyl = f.read()

with open('bootstrap/hsharpmyl_extended.hto', 'r') as f:
    extended = f.read()

with open('bootstrap/hsharpmyl_sections_19_24.hto', 'r') as f:
    sections_19_24 = f.read()

# Split hsharpmyl.hto into parts
lines = hsharpmyl.split('\n')

# Find section boundaries
sec1_start = 0  # line 1
sec6_start = None  # "SECTION 6: Preprocessing"
sec11_start = None  # "SECTION 11: Probability Distributions"
summary_start = None  # "Summary"

for i, line in enumerate(lines):
    if 'SECTION 6: Preprocessing' in line:
        sec6_start = i
    if 'SECTION 11: Probability Distributions' in line:
        sec11_start = i
    if line.strip().startswith('# ═') and 'Summary' in lines[i+1] if i+1 < len(lines) else False:
        pass
    if 'SUMMARY' in line.upper() or 'Summary' in line:
        if i > len(lines) - 100:
            summary_start = i
            break

# Find summary more carefully
for i in range(len(lines) - 1, len(lines) - 50, -1):
    if 'SUMMARY' in lines[i].upper() or 'Summary' in lines[i]:
        summary_start = i
        break

# Also find the end of Section 13 (Feature Engineering) and start of Section 14 (Optimizers)
sec14_start = None
for i, line in enumerate(lines):
    if 'SECTION 14: Optimization' in line or 'Optimizers' in line:
        sec14_start = i
        break

print(f"Section boundaries: sec6={sec6_start}, sec11={sec11_start}, sec14={sec14_start}, summary={summary_start}")

# Extract the parts
# Part 1: Sections 1-5 (lines 0 to sec6_start-1)
part1 = '\n'.join(lines[0:sec6_start])

# Original Sections 6-12 (Preprocessing, Linear Reg, Logistic Reg, KNN, KMeans, Decision Tree, MLP)
# This is from sec6_start to sec11_start-1
part3 = '\n'.join(lines[sec6_start:sec11_start])

# Sections 11-14 (Probability, Tests, Feature Eng, Optimizers)
# This is from sec11_start to summary_start
part4 = '\n'.join(lines[sec11_start:summary_start])

# Now generate Sections 15-18

sec15 = """# ═══════════════════════════════════════════════════════════════════════════
# SECTION 15: Ensemble Models
# ═══════════════════════════════════════════════════════════════════════════

# ── Voting Classifier ──

class VotingClassifier {
    let estimators = [];
    let mode = "hard";
    let fitted = false;

    fn init_voting(estimators, mode) {
        self.estimators = estimators;
        if (mode != nullptr) { self.mode = mode; }
        self.fitted = false;
        return 0;
    }

    fn fit(X, y) {
        let i = 0;
        while (i < len(self.estimators)) {
            let est = self.estimators[i];
            let model = est[1];
            let fit_method = model["fit"];
            if (fit_method != nullptr) {
                fit_method(X, y);
            }
            i = i + 1;
        }
        self.fitted = true;
        return 0;
    }

    fn predict(X) {
        let n = len(X);
        let result = [];
        let i = 0;
        while (i < n) {
            let votes = {};
            let j = 0;
            while (j < len(self.estimators)) {
                let model = self.estimators[j][1];
                let predict_method = model["predict"];
                let pred = [];
                if (predict_method != nullptr) {
                    pred = predict_method([X[i]]);
                }
                if (len(pred) > 0) {
                    let lbl = pred[0];
                    let cnt = votes[lbl];
                    if (cnt == nullptr) {
                        votes[lbl] = 1;
                    } else {
                        votes[lbl] = cnt + 1;
                    }
                }
                j = j + 1;
            }
            if (self.mode == "soft") {
                let prob_sums = {};
                let j = 0;
                while (j < len(self.estimators)) {
                    let model = self.estimators[j][1];
                    let proba_method = model["predict_proba"];
                    if (proba_method != nullptr) {
                        let probs = proba_method([X[i]]);
                        let k = 0;
                        while (k < len(probs)) {
                            let lbl = k;
                            let prob = probs[k];
                            let cur = prob_sums[lbl];
                            if (cur == nullptr) {
                                prob_sums[lbl] = prob;
                            } else {
                                prob_sums[lbl] = cur + prob;
                            }
                            k = k + 1;
                        }
                    }
                    j = j + 1;
                }
                let best_lbl = 0;
                let best_prob = 0.0;
                let keys = dict_keys(prob_sums);
                let ki = 0;
                while (ki < len(keys)) {
                    let lbl = keys[ki];
                    let p = prob_sums[lbl];
                    if (p > best_prob) {
                        best_prob = p;
                        best_lbl = lbl;
                    }
                    ki = ki + 1;
                }
                push(result, best_lbl);
            } else {
                let best_lbl = 0;
                let best_cnt = 0;
                let keys = dict_keys(votes);
                let ki = 0;
                while (ki < len(keys)) {
                    let lbl = keys[ki];
                    let cnt = votes[lbl];
                    if (cnt > best_cnt) {
                        best_cnt = cnt;
                        best_lbl = lbl;
                    }
                    ki = ki + 1;
                }
                push(result, best_lbl);
            }
            i = i + 1;
        }
        return result;
    }

    fn predict_proba(X) {
        let n = len(X);
        let result = [];
        let i = 0;
        while (i < n) {
            let prob_sums = {};
            let n_estimators = 0;
            let j = 0;
            while (j < len(self.estimators)) {
                let model = self.estimators[j][1];
                let proba_method = model["predict_proba"];
                if (proba_method != nullptr) {
                    let probs = proba_method([X[i]]);
                    let k = 0;
                    while (k < len(probs)) {
                        let lbl = k;
                        let prob = probs[k];
                        let cur = prob_sums[lbl];
                        if (cur == nullptr) {
                            prob_sums[lbl] = prob;
                        } else {
                            prob_sums[lbl] = cur + prob;
                        }
                        k = k + 1;
                    }
                    n_estimators = n_estimators + 1;
                }
                j = j + 1;
            }
            let avg_probs = [];
            let keys = dict_keys(prob_sums);
            let ki = 0;
            while (ki < len(keys)) {
                push(avg_probs, prob_sums[keys[ki]] * 1.0 / n_estimators);
                ki = ki + 1;
            }
            push(result, avg_probs);
            i = i + 1;
        }
        return result;
    }

    fn score(X, y) {
        let y_pred = self.predict(X);
        return accuracy_score(y, y_pred);
    }
}

# ── Bagging Classifier ──

class BaggingClassifier {
    let base_estimator_class = nullptr;
    let n_estimators = 10;
    let sample_ratio = 0.8;
    let estimators = [];
    let fitted = false;

    fn init_bagging(base_estimator_class, n_estimators, sample_ratio) {
        self.base_estimator_class = base_estimator_class;
        self.n_estimators = n_estimators;
        self.sample_ratio = sample_ratio;
        self.estimators = [];
        self.fitted = false;
        return 0;
    }

    fn fit(X, y) {
        let n = len(X);
        let sample_size = math_floor(n * self.sample_ratio);
        if (sample_size < 1) { sample_size = 1; }
        self.estimators = [];
        let t = 0;
        while (t < self.n_estimators) {
            let X_sample = [];
            let y_sample = [];
            let i = 0;
            while (i < sample_size) {
                let idx = hml_randint(0, n - 1);
                push(X_sample, X[idx]);
                push(y_sample, y[idx]);
                i = i + 1;
            }
            let model = self.base_estimator_class();
            let init_method = model["init_dtree"];
            if (init_method == nullptr) {
                init_method = model["init_logistic"];
            }
            if (init_method == nullptr) {
                init_method = model["init_knn"];
            }
            if (init_method != nullptr) {
                init_method(5, 2);
            }
            let fit_method = model["fit"];
            if (fit_method != nullptr) {
                fit_method(X_sample, y_sample);
            }
            push(self.estimators, model);
            t = t + 1;
        }
        self.fitted = true;
        return 0;
    }

    fn predict(X) {
        let n = len(X);
        let result = [];
        let i = 0;
        while (i < n) {
            let votes = {};
            let j = 0;
            while (j < len(self.estimators)) {
                let model = self.estimators[j];
                let predict_method = model["predict"];
                let pred = [];
                if (predict_method != nullptr) {
                    pred = predict_method([X[i]]);
                }
                if (len(pred) > 0) {
                    let lbl = pred[0];
                    let cnt = votes[lbl];
                    if (cnt == nullptr) {
                        votes[lbl] = 1;
                    } else {
                        votes[lbl] = cnt + 1;
                    }
                }
                j = j + 1;
            }
            let best_lbl = 0;
            let best_cnt = 0;
            let keys = dict_keys(votes);
            let ki = 0;
            while (ki < len(keys)) {
                let lbl = keys[ki];
                let cnt = votes[lbl];
                if (cnt > best_cnt) {
                    best_cnt = cnt;
                    best_lbl = lbl;
                }
                ki = ki + 1;
            }
            push(result, best_lbl);
            i = i + 1;
        }
        return result;
    }

    fn score(X, y) {
        let y_pred = self.predict(X);
        return accuracy_score(y, y_pred);
    }
}

# ── AdaBoost Classifier ──

class AdaBoostClassifier {
    let n_estimators = 50;
    let learning_rate = 1.0;
    let estimators = [];
    let estimator_weights = [];
    let fitted = false;

    fn init_adaboost(n_estimators, learning_rate) {
        self.n_estimators = n_estimators;
        self.learning_rate = learning_rate;
        self.estimators = [];
        self.estimator_weights = [];
        self.fitted = false;
        return 0;
    }

    fn fit(X, y) {
        let n = len(X);
        let sample_weights = [];
        let i = 0;
        while (i < n) {
            push(sample_weights, 1.0 / n);
            i = i + 1;
        }
        self.estimators = [];
        self.estimator_weights = [];
        let t = 0;
        while (t < self.n_estimators) {
            let stump = DecisionTreeClassifier();
            stump.init_dtree(1, 2);
            let X_sample = [];
            let y_sample = [];
            let cumsum = 0.0;
            let j = 0;
            while (j < n) {
                cumsum = cumsum + sample_weights[j];
                j = j + 1;
            }
            let i = 0;
            while (i < n) {
                let r = hml_random() * cumsum;
                let cs = 0.0;
                let idx = 0;
                let k = 0;
                while (k < n) {
                    cs = cs + sample_weights[k];
                    if (cs >= r) {
                        idx = k;
                        break;
                    }
                    k = k + 1;
                }
                push(X_sample, X[idx]);
                push(y_sample, y[idx]);
                i = i + 1;
            }
            stump.fit(X_sample, y_sample);
            let y_pred = stump.predict(X);
            let error = 0.0;
            i = 0;
            while (i < n) {
                if (y_pred[i] != y[i]) {
                    error = error + sample_weights[i];
                }
                i = i + 1;
            }
            if (error > 0.5) {
                t = t + 1;
                continue;
            }
            if (error == 0.0) { error = 0.0000001; }
            let alpha = self.learning_rate * 0.5 * math_log((1.0 - error) / error);
            if (alpha < 0.0) { alpha = 0.0; }
            push(self.estimators, stump);
            push(self.estimator_weights, alpha);
            let total_w = 0.0;
            i = 0;
            while (i < n) {
                if (y_pred[i] == y[i]) {
                    sample_weights[i] = sample_weights[i] * math_exp(-alpha);
                } else {
                    sample_weights[i] = sample_weights[i] * math_exp(alpha);
                }
                total_w = total_w + sample_weights[i];
                i = i + 1;
            }
            i = 0;
            while (i < n) {
                sample_weights[i] = sample_weights[i] / total_w;
                i = i + 1;
            }
            t = t + 1;
        }
        self.fitted = true;
        return 0;
    }

    fn predict(X) {
        let n = len(X);
        let result = [];
        let i = 0;
        while (i < n) {
            let scores = {};
            let j = 0;
            while (j < len(self.estimators)) {
                let model = self.estimators[j];
                let pred = model.predict([X[i]]);
                if (len(pred) > 0) {
                    let lbl = pred[0];
                    let weight = self.estimator_weights[j];
                    let cur = scores[lbl];
                    if (cur == nullptr) {
                        scores[lbl] = weight;
                    } else {
                        scores[lbl] = cur + weight;
                    }
                }
                j = j + 1;
            }
            let best_lbl = 0;
            let best_score = -1.0;
            let keys = dict_keys(scores);
            let ki = 0;
            while (ki < len(keys)) {
                let lbl = keys[ki];
                let s = scores[lbl];
                if (s > best_score) {
                    best_score = s;
                    best_lbl = lbl;
                }
                ki = ki + 1;
            }
            push(result, best_lbl);
            i = i + 1;
        }
        return result;
    }

    fn score(X, y) {
        let y_pred = self.predict(X);
        return accuracy_score(y, y_pred);
    }
}

# ── Gradient Boosting Classifier ──

class GradientBoostingClassifier {
    let n_estimators = 100;
    let learning_rate = 0.1;
    let max_depth = 3;
    let estimators = [];
    let initial_prob = 0.0;
    let fitted = false;

    fn init_gbdt(n_estimators, learning_rate, max_depth) {
        self.n_estimators = n_estimators;
        self.learning_rate = learning_rate;
        if (max_depth == nullptr) { self.max_depth = 3; }
        self.estimators = [];
        self.initial_prob = 0.0;
        self.fitted = false;
        return 0;
    }

    fn _sigmoid(z) {
        return 1.0 / (1.0 + math_exp(-z));
    }

    fn fit(X, y) {
        let n = len(X);
        let pos_cnt = 0;
        let i = 0;
        while (i < n) {
            if (y[i] == 1) { pos_cnt = pos_cnt + 1; }
            i = i + 1;
        }
        self.initial_prob = pos_cnt * 1.0 / n;
        if (self.initial_prob < 0.0001) { self.initial_prob = 0.0001; }
        if (self.initial_prob > 0.9999) { self.initial_prob = 0.9999; }
        let current_probs = [];
        i = 0;
        while (i < n) {
            push(current_probs, self.initial_prob);
            i = i + 1;
        }
        self.estimators = [];
        let t = 0;
        while (t < self.n_estimators) {
            let residuals = [];
            i = 0;
            while (i < n) {
                let r = y[i] - current_probs[i];
                push(residuals, r);
                i = i + 1;
            }
            let tree = DecisionTreeClassifier();
            tree.init_dtree(self.max_depth, 2);
            let y_approx = [];
            i = 0;
            while (i < n) {
                if (residuals[i] >= 0.0) {
                    push(y_approx, 1);
                } else {
                    push(y_approx, 0);
                }
                i = i + 1;
            }
            tree.fit(X, y_approx);
            push(self.estimators, tree);
            let preds = tree.predict(X);
            i = 0;
            while (i < n) {
                let update = 0.0;
                if (preds[i] == 1) {
                    update = self.learning_rate * 1.0;
                } else {
                    update = -self.learning_rate * 1.0;
                }
                current_probs[i] = self._sigmoid(math_log(current_probs[i] / (1.0 - current_probs[i] + 0.0000001)) + update);
                i = i + 1;
            }
            t = t + 1;
        }
        self.fitted = true;
        return 0;
    }

    fn predict_proba(X) {
        let n = len(X);
        let log_odds = [];
        let i = 0;
        while (i < n) {
            push(log_odds, math_log(self.initial_prob / (1.0 - self.initial_prob + 0.0000001)));
            i = i + 1;
        }
        let t = 0;
        while (t < len(self.estimators)) {
            let tree = self.estimators[t];
            let preds = tree.predict(X);
            i = 0;
            while (i < n) {
                if (preds[i] == 1) {
                    log_odds[i] = log_odds[i] + self.learning_rate * 1.0;
                } else {
                    log_odds[i] = log_odds[i] - self.learning_rate * 1.0;
                }
                i = i + 1;
            }
            t = t + 1;
        }
        let result = [];
        i = 0;
        while (i < n) {
            push(result, self._sigmoid(log_odds[i]));
            i = i + 1;
        }
        return result;
    }

    fn predict(X) {
        let probas = self.predict_proba(X);
        let result = [];
        let i = 0;
        while (i < len(probas)) {
            if (probas[i] >= 0.5) {
                push(result, 1);
            } else {
                push(result, 0);
            }
            i = i + 1;
        }
        return result;
    }

    fn score(X, y) {
        let y_pred = self.predict(X);
        return accuracy_score(y, y_pred);
    }
}
"""

sec16 = """# ═══════════════════════════════════════════════════════════════════════════
# SECTION 16: Cross Validation
# ═══════════════════════════════════════════════════════════════════════════

# ── K-Fold Split ──

fn kfold_split(n_samples, n_folds, shuffle) {
    let indices = [];
    let i = 0;
    while (i < n_samples) {
        push(indices, i);
        i = i + 1;
    }
    if (shuffle == true) {
        hml_shuffle(indices);
    }
    let folds = [];
    let fold_size = math_floor(n_samples * 1.0 / n_folds);
    let remainder = n_samples - fold_size * n_folds;
    let start = 0;
    let f = 0;
    while (f < n_folds) {
        let size = fold_size;
        if (f < remainder) { size = size + 1; }
        let fold = [];
        let j = 0;
        while (j < size) {
            push(fold, indices[start + j]);
            j = j + 1;
        }
        push(folds, fold);
        start = start + size;
        f = f + 1;
    }
    let result = [];
    f = 0;
    while (f < n_folds) {
        let test_indices = folds[f];
        let train_indices = [];
        let g = 0;
        while (g < n_folds) {
            if (g != f) {
                let j = 0;
                while (j < len(folds[g])) {
                    push(train_indices, folds[g][j]);
                    j = j + 1;
                }
            }
            g = g + 1;
        }
        push(result, {"train_indices": train_indices, "test_indices": test_indices});
        f = f + 1;
    }
    return result;
}

# ── Stratified K-Fold Split ──

fn stratified_kfold_split(y, n_folds) {
    let n = len(y);
    let unique_labels = hml_unique(y);
    let label_indices = {};
    let i = 0;
    while (i < len(unique_labels)) {
        label_indices[unique_labels[i]] = [];
        i = i + 1;
    }
    i = 0;
    while (i < n) {
        let lbl = y[i];
        push(label_indices[lbl], i);
        i = i + 1;
    }
    let folds = [];
    let f = 0;
    while (f < n_folds) {
        push(folds, []);
        f = f + 1;
    }
    let li = 0;
    while (li < len(unique_labels)) {
        let lbl = unique_labels[li];
        let indices = label_indices[lbl];
        hml_shuffle(indices);
        let fi = 0;
        while (fi < len(indices)) {
            let fold_idx = fi % n_folds;
            push(folds[fold_idx], indices[fi]);
            fi = fi + 1;
        }
        li = li + 1;
    }
    let result = [];
    f = 0;
    while (f < n_folds) {
        let test_indices = folds[f];
        let train_indices = [];
        let g = 0;
        while (g < n_folds) {
            if (g != f) {
                let j = 0;
                while (j < len(folds[g])) {
                    push(train_indices, folds[g][j]);
                    j = j + 1;
                }
            }
            g = g + 1;
        }
        push(result, {"train_indices": train_indices, "test_indices": test_indices});
        f = f + 1;
    }
    return result;
}

# ── Cross Validation Score ──

fn cross_val_score(estimator, X, y, cv_folds, scoring_fn) {
    let scores = [];
    let f = 0;
    while (f < len(cv_folds)) {
        let fold = cv_folds[f];
        let train_idx = fold["train_indices"];
        let test_idx = fold["test_indices"];
        let X_train = [];
        let y_train = [];
        let X_test = [];
        let y_test = [];
        let i = 0;
        while (i < len(train_idx)) {
            push(X_train, X[train_idx[i]]);
            push(y_train, y[train_idx[i]]);
            i = i + 1;
        }
        i = 0;
        while (i < len(test_idx)) {
            push(X_test, X[test_idx[i]]);
            push(y_test, y[test_idx[i]]);
            i = i + 1;
        }
        let fit_method = estimator["fit"];
        if (fit_method != nullptr) {
            fit_method(X_train, y_train);
        }
        let predict_method = estimator["predict"];
        let y_pred = [];
        if (predict_method != nullptr) {
            y_pred = predict_method(X_test);
        }
        let score = scoring_fn(y_test, y_pred);
        push(scores, score);
        f = f + 1;
    }
    return scores;
}

# ── Cross Validation Predict ──

fn cross_val_predict(estimator, X, y, cv_folds) {
    let n = len(X);
    let predictions = [];
    let i = 0;
    while (i < n) {
        push(predictions, 0);
        i = i + 1;
    }
    let f = 0;
    while (f < len(cv_folds)) {
        let fold = cv_folds[f];
        let train_idx = fold["train_indices"];
        let test_idx = fold["test_indices"];
        let X_train = [];
        let y_train = [];
        let X_test = [];
        let i = 0;
        while (i < len(train_idx)) {
            push(X_train, X[train_idx[i]]);
            push(y_train, y[train_idx[i]]);
            i = i + 1;
        }
        i = 0;
        while (i < len(test_idx)) {
            push(X_test, X[test_idx[i]]);
            i = i + 1;
        }
        let fit_method = estimator["fit"];
        if (fit_method != nullptr) {
            fit_method(X_train, y_train);
        }
        let predict_method = estimator["predict"];
        let y_pred = [];
        if (predict_method != nullptr) {
            y_pred = predict_method(X_test);
        }
        i = 0;
        while (i < len(test_idx)) {
            predictions[test_idx[i]] = y_pred[i];
            i = i + 1;
        }
        f = f + 1;
    }
    return predictions;
}

# ── Cross Validate ──

fn cross_validate(estimator, X, y, cv_folds, scoring_fns) {
    let result = {};
    let fn_idx = 0;
    while (fn_idx < len(scoring_fns)) {
        let fn_name = scoring_fns[fn_idx][0];
        let fn_obj = scoring_fns[fn_idx][1];
        result[fn_name] = [];
        fn_idx = fn_idx + 1;
    }
    let f = 0;
    while (f < len(cv_folds)) {
        let fold = cv_folds[f];
        let train_idx = fold["train_indices"];
        let test_idx = fold["test_indices"];
        let X_train = [];
        let y_train = [];
        let X_test = [];
        let y_test = [];
        let i = 0;
        while (i < len(train_idx)) {
            push(X_train, X[train_idx[i]]);
            push(y_train, y[train_idx[i]]);
            i = i + 1;
        }
        i = 0;
        while (i < len(test_idx)) {
            push(X_test, X[test_idx[i]]);
            push(y_test, y[test_idx[i]]);
            i = i + 1;
        }
        let fit_method = estimator["fit"];
        if (fit_method != nullptr) {
            fit_method(X_train, y_train);
        }
        let predict_method = estimator["predict"];
        let y_pred = [];
        if (predict_method != nullptr) {
            y_pred = predict_method(X_test);
        }
        fn_idx = 0;
        while (fn_idx < len(scoring_fns)) {
            let fn_name = scoring_fns[fn_idx][0];
            let fn_obj = scoring_fns[fn_idx][1];
            let score = fn_obj(y_test, y_pred);
            push(result[fn_name], score);
            fn_idx = fn_idx + 1;
        }
        f = f + 1;
    }
    return result;
}

# ── Grid Search CV ──

fn grid_search_cv(estimator_class, X, y, param_grid, cv_folds, scoring_fn) {
    let keys = dict_keys(param_grid);
    let best_score = -1.0;
    let best_params = {};
    let best_estimator = nullptr;
    if (len(keys) == 0) { return {"best_params": {}, "best_score": 0.0, "best_estimator": nullptr}; }
    let key0 = keys[0];
    let values = param_grid[key0];
    let vi = 0;
    while (vi < len(values)) {
        let params = {};
        params[key0] = values[vi];
        let model = estimator_class();
        let init_method = model["init_dtree"];
        if (init_method == nullptr) {
            init_method = model["init_logistic"];
        }
        if (init_method == nullptr) {
            init_method = model["init_knn"];
        }
        if (init_method != nullptr) {
            let arg0 = params[key0];
            init_method(arg0, 2);
        }
        let scores = cross_val_score(model, X, y, cv_folds, scoring_fn);
        let avg = 0.0;
        let si = 0;
        while (si < len(scores)) {
            avg = avg + scores[si];
            si = si + 1;
        }
        if (len(scores) > 0) { avg = avg * 1.0 / len(scores); }
        if (avg > best_score) {
            best_score = avg;
            best_params = params;
            best_estimator = model;
        }
        vi = vi + 1;
    }
    return {"best_params": best_params, "best_score": best_score, "best_estimator": best_estimator};
}

# ── Random Search CV ──

fn random_search_cv(estimator_class, X, y, param_distributions, n_iter, cv_folds, scoring_fn) {
    let keys = dict_keys(param_distributions);
    let best_score = -1.0;
    let best_params = {};
    let iter = 0;
    while (iter < n_iter) {
        let params = {};
        let ki = 0;
        while (ki < len(keys)) {
            let key = keys[ki];
            let vals = param_distributions[key];
            let idx = hml_randint(0, len(vals) - 1);
            params[key] = vals[idx];
            ki = ki + 1;
        }
        let model = estimator_class();
        let init_method = model["init_dtree"];
        if (init_method == nullptr) {
            init_method = model["init_logistic"];
        }
        if (init_method == nullptr) {
            init_method = model["init_knn"];
        }
        if (init_method != nullptr) {
            let arg0 = params[keys[0]];
            init_method(arg0, 2);
        }
        let scores = cross_val_score(model, X, y, cv_folds, scoring_fn);
        let avg = 0.0;
        let si = 0;
        while (si < len(scores)) {
            avg = avg + scores[si];
            si = si + 1;
        }
        if (len(scores) > 0) { avg = avg * 1.0 / len(scores); }
        if (avg > best_score) {
            best_score = avg;
            best_params = params;
        }
        iter = iter + 1;
    }
    return {"best_params": best_params, "best_score": best_score};
}

# ── Time Series Split ──

fn time_series_split(n_samples, n_folds) {
    let result = [];
    let f = 0;
    while (f < n_folds) {
        let test_size = math_floor(n_samples * 1.0 / (n_folds + 1));
        if (test_size < 1) { test_size = 1; }
        let train_end = n_samples - (n_folds - f) * test_size;
        let test_start = train_end;
        let test_end = test_start + test_size;
        if (test_end > n_samples) { test_end = n_samples; }
        let train_indices = [];
        let i = 0;
        while (i < train_end) {
            push(train_indices, i);
            i = i + 1;
        }
        let test_indices = [];
        i = test_start;
        while (i < test_end) {
            push(test_indices, i);
            i = i + 1;
        }
        push(result, {"train_indices": train_indices, "test_indices": test_indices});
        f = f + 1;
    }
    return result;
}

# ── Learning Curve ──

fn learning_curve(estimator_class, X, y, train_sizes, cv_folds, scoring_fn) {
    let n = len(X);
    let train_scores = [];
    let test_scores = [];
    let si = 0;
    while (si < len(train_sizes)) {
        let size = train_sizes[si];
        push(train_scores, []);
        push(test_scores, []);
        let f = 0;
        while (f < len(cv_folds)) {
            let fold = cv_folds[f];
            let train_idx = fold["train_indices"];
            let test_idx = fold["test_indices"];
            let actual_size = size;
            if (actual_size > len(train_idx)) { actual_size = len(train_idx); }
            let X_train = [];
            let y_train = [];
            let i = 0;
            while (i < actual_size) {
                push(X_train, X[train_idx[i]]);
                push(y_train, y[train_idx[i]]);
                i = i + 1;
            }
            let X_test = [];
            let y_test = [];
            i = 0;
            while (i < len(test_idx)) {
                push(X_test, X[test_idx[i]]);
                push(y_test, y[test_idx[i]]);
                i = i + 1;
            }
            let model = estimator_class();
            let init_method = model["init_dtree"];
            if (init_method == nullptr) {
                init_method = model["init_logistic"];
            }
            if (init_method != nullptr) {
                init_method(5, 2);
            }
            let fit_method = model["fit"];
            if (fit_method != nullptr) {
                fit_method(X_train, y_train);
            }
            let predict_method = model["predict"];
            let y_train_pred = [];
            let y_test_pred = [];
            if (predict_method != nullptr) {
                y_train_pred = predict_method(X_train);
                y_test_pred = predict_method(X_test);
            }
            let train_score = scoring_fn(y_train, y_train_pred);
            let test_score = scoring_fn(y_test, y_test_pred);
            push(train_scores[si], train_score);
            push(test_scores[si], test_score);
            f = f + 1;
        }
        si = si + 1;
    }
    return {"train_sizes": train_sizes, "train_scores": train_scores, "test_scores": test_scores};
}

# ── Validation Curve ──

fn validation_curve(estimator_class, X, y, param_name, param_values, cv_folds, scoring_fn) {
    let train_scores = [];
    let test_scores = [];
    let pi = 0;
    while (pi < len(param_values)) {
        let param_val = param_values[pi];
        push(train_scores, []);
        push(test_scores, []);
        let f = 0;
        while (f < len(cv_folds)) {
            let fold = cv_folds[f];
            let train_idx = fold["train_indices"];
            let test_idx = fold["test_indices"];
            let X_train = [];
            let y_train = [];
            let X_test = [];
            let y_test = [];
            let i = 0;
            while (i < len(train_idx)) {
                push(X_train, X[train_idx[i]]);
                push(y_train, y[train_idx[i]]);
                i = i + 1;
            }
            i = 0;
            while (i < len(test_idx)) {
                push(X_test, X[test_idx[i]]);
                push(y_test, y[test_idx[i]]);
                i = i + 1;
            }
            let model = estimator_class();
            let init_method = model["init_dtree"];
            if (init_method == nullptr) {
                init_method = model["init_logistic"];
            }
            if (init_method == nullptr) {
                init_method = model["init_knn"];
            }
            if (init_method != nullptr) {
                init_method(param_val, 2);
            }
            let fit_method = model["fit"];
            if (fit_method != nullptr) {
                fit_method(X_train, y_train);
            }
            let predict_method = model["predict"];
            let y_train_pred = [];
            let y_test_pred = [];
            if (predict_method != nullptr) {
                y_train_pred = predict_method(X_train);
                y_test_pred = predict_method(X_test);
            }
            let train_score = scoring_fn(y_train, y_train_pred);
            let test_score = scoring_fn(y_test, y_test_pred);
            push(train_scores[pi], train_score);
            push(test_scores[pi], test_score);
            f = f + 1;
        }
        pi = pi + 1;
    }
    return {"param_name": param_name, "param_values": param_values, "train_scores": train_scores, "test_scores": test_scores};
}
"""

sec17 = """# ═══════════════════════════════════════════════════════════════════════════
# SECTION 17: Dimensionality Reduction
# ═══════════════════════════════════════════════════════════════════════════

# ── PCA ──

class PCA {
    let n_components = 2;
    let components = [];
    let mean = [];
    let explained_variance_ratio = [];
    let fitted = false;

    fn init_pca(n_components) {
        self.n_components = n_components;
        self.components = [];
        self.mean = [];
        self.explained_variance_ratio = [];
        self.fitted = false;
        return 0;
    }

    fn fit(X) {
        let n = len(X);
        let n_features = len(X[0]);
        self.mean = hml_column_means(X);
        let centered = [];
        let i = 0;
        while (i < n) {
            let row = [];
            let j = 0;
            while (j < n_features) {
                push(row, X[i][j] - self.mean[j]);
                j = j + 1;
            }
            push(centered, row);
            i = i + 1;
        }
        let cov = hml_matrix_zeros(n_features, n_features);
        i = 0;
        while (i < n_features) {
            let j = 0;
            while (j < n_features) {
                let s = 0.0;
                let k = 0;
                while (k < n) {
                    s = s + centered[k][i] * centered[k][j];
                    k = k + 1;
                }
                cov[i][j] = s * 1.0 / (n - 1);
                j = j + 1;
            }
            i = i + 1;
        }
        let eigenvalues = [];
        let eigenvectors = [];
        let comp = 0;
        while (comp < self.n_components and comp < n_features) {
            let v = [];
            i = 0;
            while (i < n_features) {
                push(v, hml_random());
                i = i + 1;
            }
            let norm = 0.0;
            i = 0;
            while (i < n_features) {
                norm = norm + v[i] * v[i];
                i = i + 1;
            }
            norm = math_sqrt(norm);
            if (norm > 0.0) {
                i = 0;
                while (i < n_features) {
                    v[i] = v[i] / norm;
                    i = i + 1;
                }
            }
            let iter = 0;
            while (iter < 50) {
                let new_v = [];
                i = 0;
                while (i < n_features) {
                    let s = 0.0;
                    let j = 0;
                    while (j < n_features) {
                        s = s + cov[i][j] * v[j];
                        j = j + 1;
                    }
                    push(new_v, s);
                    i = i + 1;
                }
                let nnorm = 0.0;
                i = 0;
                while (i < n_features) {
                    nnorm = nnorm + new_v[i] * new_v[i];
                    i = i + 1;
                }
                nnorm = math_sqrt(nnorm);
                if (nnorm > 0.0) {
                    i = 0;
                    while (i < n_features) {
                        new_v[i] = new_v[i] / nnorm;
                        i = i + 1;
                    }
                }
                v = new_v;
                iter = iter + 1;
            }
            let eig_val = 0.0;
            i = 0;
            while (i < n_features) {
                let s = 0.0;
                let j = 0;
                while (j < n_features) {
                    s = s + cov[i][j] * v[j];
                    j = j + 1;
                }
                eig_val = eig_val + v[i] * s;
                i = i + 1;
            }
            push(eigenvalues, eig_val);
            push(eigenvectors, v);
            i = 0;
            while (i < n_features) {
                let j = 0;
                while (j < n_features) {
                    cov[i][j] = cov[i][j] - eig_val * v[i] * v[j];
                    j = j + 1;
                }
                i = i + 1;
            }
            comp = comp + 1;
        }
        self.components = eigenvectors;
        let total_var = 0.0;
        let ei = 0;
        while (ei < len(eigenvalues)) {
            total_var = total_var + eigenvalues[ei];
            ei = ei + 1;
        }
        self.explained_variance_ratio = [];
        ei = 0;
        while (ei < len(eigenvalues)) {
            if (total_var > 0.0) {
                push(self.explained_variance_ratio, eigenvalues[ei] / total_var);
            } else {
                push(self.explained_variance_ratio, 0.0);
            }
            ei = ei + 1;
        }
        self.fitted = true;
        return 0;
    }

    fn transform(X) {
        let n = len(X);
        let n_features = len(X[0]);
        let result = [];
        let i = 0;
        while (i < n) {
            let row = [];
            let j = 0;
            while (j < self.n_components and j < len(self.components)) {
                let s = 0.0;
                let k = 0;
                while (k < n_features) {
                    s = s + (X[i][k] - self.mean[k]) * self.components[j][k];
                    k = k + 1;
                }
                push(row, s);
                j = j + 1;
            }
            push(result, row);
            i = i + 1;
        }
        return result;
    }

    fn fit_transform(X) {
        self.fit(X);
        return self.transform(X);
    }

    fn inverse_transform(X) {
        let n = len(X);
        let n_features = len(self.mean);
        let result = [];
        let i = 0;
        while (i < n) {
            let row = [];
            let j = 0;
            while (j < n_features) {
                row[j] = self.mean[j];
                let c = 0;
                while (c < self.n_components and c < len(self.components)) {
                    row[j] = row[j] + X[i][c] * self.components[c][j];
                    c = c + 1;
                }
                j = j + 1;
            }
            push(result, row);
            i = i + 1;
        }
        return result;
    }

    fn get_explained_variance_ratio() {
        return self.explained_variance_ratio;
    }
}

# ── Covariance Matrix ──

fn covariance_matrix(X) {
    let n = len(X);
    let n_features = len(X[0]);
    let means = hml_column_means(X);
    let cov = hml_matrix_zeros(n_features, n_features);
    let i = 0;
    while (i < n_features) {
        let j = 0;
        while (j < n_features) {
            let s = 0.0;
            let k = 0;
            while (k < n) {
                s = s + (X[k][i] - means[i]) * (X[k][j] - means[j]);
                k = k + 1;
            }
            cov[i][j] = s * 1.0 / (n - 1);
            j = j + 1;
        }
        i = i + 1;
    }
    return cov;
}

# ── Correlation Matrix ──

fn correlation_matrix(X) {
    let n = len(X);
    let n_features = len(X[0]);
    let means = hml_column_means(X);
    let stds = hml_column_stds(X);
    let corr = hml_matrix_zeros(n_features, n_features);
    let i = 0;
    while (i < n_features) {
        let j = 0;
        while (j < n_features) {
            let s = 0.0;
            let k = 0;
            while (k < n) {
                s = s + (X[k][i] - means[i]) * (X[k][j] - means[j]);
                k = k + 1;
            }
            let den = stds[i] * stds[j] * (n - 1);
            if (den == 0.0) {
                corr[i][j] = 0.0;
            } else {
                corr[i][j] = s / den;
            }
            j = j + 1;
        }
        i = i + 1;
    }
    return corr;
}

# ── SVD Power Iteration ──

fn svd_power_iteration(A, n_components, n_iter) {
    let n_rows = len(A);
    let n_cols = len(A[0]);
    let components = [];
    let residual = [];
    let i = 0;
    while (i < n_rows) {
        let row = [];
        let j = 0;
        while (j < n_cols) {
            push(row, A[i][j]);
            j = j + 1;
        }
        push(residual, row);
        i = i + 1;
    }
    let comp = 0;
    while (comp < n_components and comp < n_cols) {
        let v = [];
        i = 0;
        while (i < n_cols) {
            push(v, hml_random());
            i = i + 1;
        }
        let norm = 0.0;
        i = 0;
        while (i < n_cols) {
            norm = norm + v[i] * v[i];
            i = i + 1;
        }
        norm = math_sqrt(norm);
        if (norm > 0.0) {
            i = 0;
            while (i < n_cols) {
                v[i] = v[i] / norm;
                i = i + 1;
            }
        }
        let iter = 0;
        while (iter < n_iter) {
            let AtA_v = [];
            i = 0;
            while (i < n_cols) {
                let s = 0.0;
                let k = 0;
                while (k < n_rows) {
                    let row_dot = 0.0;
                    let j = 0;
                    while (j < n_cols) {
                        row_dot = row_dot + residual[k][j] * v[j];
                        j = j + 1;
                    }
                    s = s + residual[k][i] * row_dot;
                    k = k + 1;
                }
                push(AtA_v, s);
                i = i + 1;
            }
            let nn = 0.0;
            i = 0;
            while (i < n_cols) {
                nn = nn + AtA_v[i] * AtA_v[i];
                i = i + 1;
            }
            nn = math_sqrt(nn);
            if (nn > 0.0) {
                i = 0;
                while (i < n_cols) {
                    AtA_v[i] = AtA_v[i] / nn;
                    i = i + 1;
                }
            }
            v = AtA_v;
            iter = iter + 1;
        }
        push(components, v);
        let sig_val = 0.0;
        i = 0;
        while (i < n_cols) {
            let s = 0.0;
            let k = 0;
            while (k < n_rows) {
                let row_dot = 0.0;
                let j = 0;
                while (j < n_cols) {
                    row_dot = row_dot + residual[k][j] * v[j];
                    j = j + 1;
                }
                s = s + residual[k][i] * row_dot;
                k = k + 1;
            }
            sig_val = sig_val + v[i] * s;
            i = i + 1;
        }
        sig_val = math_sqrt(sig_val);
        let u = [];
        i = 0;
        while (i < n_rows) {
            let s = 0.0;
            let j = 0;
            while (j < n_cols) {
                s = s + residual[i][j] * v[j];
                j = j + 1;
            }
            push(u, s / sig_val);
            i = i + 1;
        }
        i = 0;
        while (i < n_rows) {
            let j = 0;
            while (j < n_cols) {
                residual[i][j] = residual[i][j] - sig_val * u[i] * v[j];
                j = j + 1;
            }
            i = i + 1;
        }
        comp = comp + 1;
    }
    return components;
}

# ── Truncated SVD ──

fn truncated_svd(X, n_components) {
    return svd_power_iteration(X, n_components, 30);
}

# ── LDA Fit ──

fn lda_fit(X, y, n_components) {
    let n = len(X);
    let n_features = len(X[0]);
    let labels = hml_unique(y);
    let n_classes = len(labels);
    let overall_mean = hml_column_means(X);
    let class_means = {};
    let class_counts = {};
    let li = 0;
    while (li < n_classes) {
        let lbl = labels[li];
        class_means[lbl] = hml_vector_zeros(n_features);
        class_counts[lbl] = 0;
        li = li + 1;
    }
    let i = 0;
    while (i < n) {
        let lbl = y[i];
        let cnt = class_counts[lbl];
        class_counts[lbl] = cnt + 1;
        let j = 0;
        while (j < n_features) {
            class_means[lbl][j] = class_means[lbl][j] + X[i][j];
            j = j + 1;
        }
        i = i + 1;
    }
    li = 0;
    while (li < n_classes) {
        let lbl = labels[li];
        let cnt = class_counts[lbl];
        if (cnt > 0) {
            let j = 0;
            while (j < n_features) {
                class_means[lbl][j] = class_means[lbl][j] * 1.0 / cnt;
                j = j + 1;
            }
        }
        li = li + 1;
    }
    let S_W = hml_matrix_zeros(n_features, n_features);
    i = 0;
    while (i < n) {
        let lbl = y[i];
        let mean = class_means[lbl];
        let r = 0;
        while (r < n_features) {
            let c = 0;
            while (c < n_features) {
                S_W[r][c] = S_W[r][c] + (X[i][r] - mean[r]) * (X[i][c] - mean[c]);
                c = c + 1;
            }
            r = r + 1;
        }
        i = i + 1;
    }
    let S_B = hml_matrix_zeros(n_features, n_features);
    li = 0;
    while (li < n_classes) {
        let lbl = labels[li];
        let mean = class_means[lbl];
        let cnt = class_counts[lbl];
        let r = 0;
        while (r < n_features) {
            let c = 0;
            while (c < n_features) {
                S_B[r][c] = S_B[r][c] + cnt * (mean[r] - overall_mean[r]) * (mean[c] - overall_mean[c]);
                c = c + 1;
            }
            r = r + 1;
        }
        li = li + 1;
    }
    let S_W_inv = hml_matrix_zeros(n_features, n_features);
    let ri = 0;
    while (ri < n_features) {
        S_W_inv[ri][ri] = 1.0;
        ri = ri + 1;
    }
    ri = 0;
    while (ri < n_features) {
        let pivot = S_W[ri][ri];
        if (math_fabs(pivot) < 0.0000000001) { pivot = 1.0; }
        let c = 0;
        while (c < n_features) {
            S_W[ri][c] = S_W[ri][c] / pivot;
            S_W_inv[ri][c] = S_W_inv[ri][c] / pivot;
            c = c + 1;
        }
        let r2 = 0;
        while (r2 < n_features) {
            if (r2 != ri) {
                let factor = S_W[r2][ri];
                c = 0;
                while (c < n_features) {
                    S_W[r2][c] = S_W[r2][c] - factor * S_W[ri][c];
                    S_W_inv[r2][c] = S_W_inv[r2][c] - factor * S_W_inv[ri][c];
                    c = c + 1;
                }
            }
            r2 = r2 + 1;
        }
        ri = ri + 1;
    }
    let M = hml_matrix_multiply(S_W_inv, S_B);
    let proj = [];
    let comp = 0;
    let max_comp = n_components;
    if (max_comp > n_classes - 1) { max_comp = n_classes - 1; }
    while (comp < max_comp) {
        let v = [];
        i = 0;
        while (i < n_features) {
            push(v, hml_random());
            i = i + 1;
        }
        let norm = 0.0;
        i = 0;
        while (i < n_features) {
            norm = norm + v[i] * v[i];
            i = i + 1;
        }
        norm = math_sqrt(norm);
        if (norm > 0.0) {
            i = 0;
            while (i < n_features) {
                v[i] = v[i] / norm;
                i = i + 1;
            }
        }
        let iter = 0;
        while (iter < 30) {
            let new_v = [];
            i = 0;
            while (i < n_features) {
                let s = 0.0;
                let j = 0;
                while (j < n_features) {
                    s = s + M[i][j] * v[j];
                    j = j + 1;
                }
                push(new_v, s);
                i = i + 1;
            }
            let nn = 0.0;
            i = 0;
            while (i < n_features) {
                nn = nn + new_v[i] * new_v[i];
                i = i + 1;
            }
            nn = math_sqrt(nn);
            if (nn > 0.0) {
                i = 0;
                while (i < n_features) {
                    new_v[i] = new_v[i] / nn;
                    i = i + 1;
                }
            }
            v = new_v;
            iter = iter + 1;
        }
        push(proj, v);
        let eig_val = 0.0;
        i = 0;
        while (i < n_features) {
            let s = 0.0;
            let j = 0;
            while (j < n_features) {
                s = s + M[i][j] * v[j];
                j = j + 1;
            }
            eig_val = eig_val + v[i] * s;
            i = i + 1;
        }
        i = 0;
        while (i < n_features) {
            let j = 0;
            while (j < n_features) {
                M[i][j] = M[i][j] - eig_val * v[i] * v[j];
                j = j + 1;
            }
            i = i + 1;
        }
        comp = comp + 1;
    }
    return proj;
}

# ── LDA Transform ──

fn lda_transform(X, projection) {
    let n = len(X);
    let n_features = len(X[0]);
    let result = [];
    let i = 0;
    while (i < n) {
        let row = [];
        let j = 0;
        while (j < len(projection)) {
            let s = 0.0;
            let k = 0;
            while (k < n_features) {
                s = s + X[i][k] * projection[j][k];
                k = k + 1;
            }
            push(row, s);
            j = j + 1;
        }
        push(result, row);
        i = i + 1;
    }
    return result;
}

# ── Gaussian Random Projection ──

fn gaussian_random_projection(X, n_components) {
    let n = len(X);
    let n_features = len(X[0]);
    let proj = [];
    let i = 0;
    while (i < n_features) {
        let row = [];
        let j = 0;
        while (j < n_components) {
            let u1 = hml_random();
            let u2 = hml_random();
            let z = math_sqrt(-2.0 * math_log(u1 + 0.0000001)) * math_cos(2.0 * 3.141592653589793 * u2);
            push(row, z);
            j = j + 1;
        }
        push(proj, row);
        i = i + 1;
    }
    let result = [];
    i = 0;
    while (i < n) {
        let row = [];
        let j = 0;
        while (j < n_components) {
            let s = 0.0;
            let k = 0;
            while (k < n_features) {
                s = s + X[i][k] * proj[k][j];
                k = k + 1;
            }
            push(row, s / math_sqrt(n_components * 1.0));
            j = j + 1;
        }
        push(result, row);
        i = i + 1;
    }
    return result;
}

# ── Sparse Random Projection ──

fn sparse_random_projection(X, n_components) {
    let n = len(X);
    let n_features = len(X[0]);
    let density = 1.0 / math_sqrt(n_features * 1.0);
    let proj = [];
    let i = 0;
    while (i < n_features) {
        let row = [];
        let j = 0;
        while (j < n_components) {
            let r = hml_random();
            let val = 0.0;
            if (r < density / 2.0) {
                val = math_sqrt(1.0 / density);
            } else {
                if (r < density) {
                    val = -math_sqrt(1.0 / density);
                }
            }
            push(row, val);
            j = j + 1;
        }
        push(proj, row);
        i = i + 1;
    }
    let result = [];
    i = 0;
    while (i < n) {
        let row = [];
        let j = 0;
        while (j < n_components) {
            let s = 0.0;
            let k = 0;
            while (k < n_features) {
                s = s + X[i][k] * proj[k][j];
                k = k + 1;
            }
            push(row, s);
            j = j + 1;
        }
        push(result, row);
        i = i + 1;
    }
    return result;
}

# ── Feature Agglomeration ──

fn feature_agglomeration(X, n_clusters) {
    let n = len(X);
    let n_features = len(X[0]);
    if (n_clusters >= n_features) {
        let result = [];
        let i = 0;
        while (i < n) {
            let row = [];
            let j = 0;
            while (j < n_features) {
                push(row, X[i][j]);
                j = j + 1;
            }
            push(result, row);
            i = i + 1;
        }
        return result;
    }
    let clusters = [];
    let i = 0;
    while (i < n_features) {
        push(clusters, [i]);
        i = i + 1;
    }
    let corr = correlation_matrix(X);
    while (len(clusters) > n_clusters) {
        let best_i = -1;
        let best_j = -1;
        let best_corr = -1.0;
        let ci = 0;
        while (ci < len(clusters)) {
            let cj = ci + 1;
            while (cj < len(clusters)) {
                let avg_corr = 0.0;
                let cnt = 0;
                let fi = 0;
                while (fi < len(clusters[ci])) {
                    let fj = 0;
                    while (fj < len(clusters[cj])) {
                        let c = corr[clusters[ci][fi]][clusters[cj][fj]];
                        if (c < 0.0) { c = -c; }
                        avg_corr = avg_corr + c;
                        cnt = cnt + 1;
                        fj = fj + 1;
                    }
                    fi = fi + 1;
                }
                if (cnt > 0) { avg_corr = avg_corr * 1.0 / cnt; }
                if (avg_corr > best_corr) {
                    best_corr = avg_corr;
                    best_i = ci;
                    best_j = cj;
                }
                cj = cj + 1;
            }
            ci = ci + 1;
        }
        if (best_i >= 0 and best_j >= 0) {
            let fi = 0;
            while (fi < len(clusters[best_j])) {
                push(clusters[best_i], clusters[best_j][fi]);
                fi = fi + 1;
            }
            let new_clusters = [];
            ci = 0;
            while (ci < len(clusters)) {
                if (ci != best_j) {
                    push(new_clusters, clusters[ci]);
                }
                ci = ci + 1;
            }
            clusters = new_clusters;
        }
    }
    let result = [];
    i = 0;
    while (i < n) {
        let row = [];
        let ci = 0;
        while (ci < len(clusters)) {
            let s = 0.0;
            let fi = 0;
            while (fi < len(clusters[ci])) {
                s = s + X[i][clusters[ci][fi]];
                fi = fi + 1;
            }
            push(row, s * 1.0 / len(clusters[ci]));
            ci = ci + 1;
        }
        push(result, row);
        i = i + 1;
    }
    return result;
}
"""

sec18 = """# ═══════════════════════════════════════════════════════════════════════════
# SECTION 18: Data Augmentation
# ═══════════════════════════════════════════════════════════════════════════

# ── SMOTE Oversampling ──

fn smote(X, y, k, n_synthetic) {
    let n = len(X);
    let n_features = len(X[0]);
    let labels = hml_unique(y);
    let minority_label = labels[0];
    let min_count = 0;
    let li = 0;
    while (li < len(labels)) {
        let cnt = 0;
        let i = 0;
        while (i < n) {
            if (y[i] == labels[li]) { cnt = cnt + 1; }
            i = i + 1;
        }
        if (cnt < min_count or li == 0) {
            min_count = cnt;
            minority_label = labels[li];
        }
        li = li + 1;
    }
    let minority_indices = [];
    let i = 0;
    while (i < n) {
        if (y[i] == minority_label) {
            push(minority_indices, i);
        }
        i = i + 1;
    }
    let X_new = [];
    let y_new = [];
    i = 0;
    while (i < n) {
        push(X_new, X[i]);
        push(y_new, y[i]);
        i = i + 1;
    }
    let syn = 0;
    while (syn < n_synthetic) {
        let idx = hml_randint(0, len(minority_indices) - 1);
        let sample = minority_indices[idx];
        let neighbors = [];
        let j = 0;
        while (j < len(minority_indices)) {
            if (j != idx) {
                let d = 0.0;
                let f = 0;
                while (f < n_features) {
                    let diff = X[minority_indices[j]][f] - X[sample][f];
                    d = d + diff * diff;
                    f = f + 1;
                }
                push(neighbors, {"dist": math_sqrt(d), "idx": minority_indices[j]});
            }
            j = j + 1;
        }
        let si = 0;
        while (si < k and si < len(neighbors)) {
            let min_idx = si;
            let sj = si + 1;
            while (sj < len(neighbors)) {
                if (neighbors[sj]["dist"] < neighbors[min_idx]["dist"]) {
                    min_idx = sj;
                }
                sj = sj + 1;
            }
            let tmp = neighbors[si];
            neighbors[si] = neighbors[min_idx];
            neighbors[min_idx] = tmp;
            si = si + 1;
        }
        let nn_idx = hml_randint(0, k - 1);
        if (nn_idx >= len(neighbors)) { nn_idx = len(neighbors) - 1; }
        let neighbor = neighbors[nn_idx]["idx"];
        let new_sample = [];
        let gap = hml_random();
        let f = 0;
        while (f < n_features) {
            push(new_sample, X[sample][f] + gap * (X[neighbor][f] - X[sample][f]));
            f = f + 1;
        }
        push(X_new, new_sample);
        push(y_new, minority_label);
        syn = syn + 1;
    }
    return {"X": X_new, "y": y_new};
}

# ── Random Oversampling ──

fn random_oversample(X, y, ratio) {
    let n = len(X);
    let n_features = len(X[0]);
    let labels = hml_unique(y);
    let minority_label = labels[0];
    let min_count = 999999999;
    let li = 0;
    while (li < len(labels)) {
        let cnt = 0;
        let i = 0;
        while (i < n) {
            if (y[i] == labels[li]) { cnt = cnt + 1; }
            i = i + 1;
        }
        if (cnt < min_count) {
            min_count = cnt;
            minority_label = labels[li];
        }
        li = li + 1;
    }
    let majority_label = labels[0];
    let maj_count = 0;
    li = 0;
    while (li < len(labels)) {
        let cnt = 0;
        let i = 0;
        while (i < n) {
            if (y[i] == labels[li]) { cnt = cnt + 1; }
            i = i + 1;
        }
        if (cnt > maj_count) {
            maj_count = cnt;
            majority_label = labels[li];
        }
        li = li + 1;
    }
    let target_count = math_floor(maj_count * ratio);
    let minority_indices = [];
    let i = 0;
    while (i < n) {
        if (y[i] == minority_label) {
            push(minority_indices, i);
        }
        i = i + 1;
    }
    let X_new = [];
    let y_new = [];
    i = 0;
    while (i < n) {
        push(X_new, X[i]);
        push(y_new, y[i]);
        i = i + 1;
    }
    let extra = target_count - len(minority_indices);
    if (extra < 0) { extra = 0; }
    let e = 0;
    while (e < extra) {
        let idx = hml_randint(0, len(minority_indices) - 1);
        push(X_new, X[minority_indices[idx]]);
        push(y_new, minority_label);
        e = e + 1;
    }
    return {"X": X_new, "y": y_new};
}

# ── Random Undersampling ──

fn random_undersample(X, y, ratio) {
    let n = len(X);
    let labels = hml_unique(y);
    let majority_label = labels[0];
    let maj_count = 0;
    let li = 0;
    while (li < len(labels)) {
        let cnt = 0;
        let i = 0;
        while (i < n) {
            if (y[i] == labels[li]) { cnt = cnt + 1; }
            i = i + 1;
        }
        if (cnt > maj_count) {
            maj_count = cnt;
            majority_label = labels[li];
        }
        li = li + 1;
    }
    let minority_label = labels[0];
    let min_count = 999999999;
    li = 0;
    while (li < len(labels)) {
        let cnt = 0;
        let i = 0;
        while (i < n) {
            if (y[i] == labels[li]) { cnt = cnt + 1; }
            i = i + 1;
        }
        if (cnt < min_count) {
            min_count = cnt;
            minority_label = labels[li];
        }
        li = li + 1;
    }
    let target_count = math_floor(min_count / ratio);
    let majority_indices = [];
    let i = 0;
    while (i < n) {
        if (y[i] == majority_label) {
            push(majority_indices, i);
        }
        i = i + 1;
    }
    hml_shuffle(majority_indices);
    let keep = [];
    i = 0;
    while (i < target_count and i < len(majority_indices)) {
        push(keep, majority_indices[i]);
        i = i + 1;
    }
    let X_new = [];
    let y_new = [];
    i = 0;
    while (i < n) {
        if (y[i] != majority_label) {
            push(X_new, X[i]);
            push(y_new, y[i]);
        }
        i = i + 1;
    }
    i = 0;
    while (i < len(keep)) {
        push(X_new, X[keep[i]]);
        push(y_new, majority_label);
        i = i + 1;
    }
    return {"X": X_new, "y": y_new};
}

# ── Tomek Links Removal ──

fn tomek_links_remove(X, y) {
    let n = len(X);
    let n_features = len(X[0]);
    let tomek_pairs = [];
    let i = 0;
    while (i < n) {
        let j = i + 1;
        while (j < n) {
            if (y[i] != y[j]) {
                let d = 0.0;
                let f = 0;
                while (f < n_features) {
                    let diff = X[i][f] - X[j][f];
                    d = d + diff * diff;
                    f = f + 1;
                }
                d = math_sqrt(d);
                let is_tomek = true;
                let k = 0;
                while (k < n) {
                    if (k != i and k != j) {
                        let d1 = 0.0;
                        let d2 = 0.0;
                        let f = 0;
                        while (f < n_features) {
                            let diff1 = X[i][f] - X[k][f];
                            let diff2 = X[j][f] - X[k][f];
                            d1 = d1 + diff1 * diff1;
                            d2 = d2 + diff2 * diff2;
                            f = f + 1;
                        }
                        d1 = math_sqrt(d1);
                        d2 = math_sqrt(d2);
                        if (d1 < d or d2 < d) {
                            is_tomek = false;
                            break;
                        }
                    }
                    k = k + 1;
                }
                if (is_tomek) {
                    push(tomek_pairs, j);
                }
            }
            j = j + 1;
        }
        i = i + 1;
    }
    let remove_set = {};
    let ti = 0;
    while (ti < len(tomek_pairs)) {
        remove_set[tomek_pairs[ti]] = 1;
        ti = ti + 1;
    }
    let X_new = [];
    let y_new = [];
    i = 0;
    while (i < n) {
        if (remove_set[i] == nullptr) {
            push(X_new, X[i]);
            push(y_new, y[i]);
        }
        i = i + 1;
    }
    return {"X": X_new, "y": y_new};
}

# ── Class Weight Balanced ──

fn class_weight_balanced(y) {
    let n = len(y);
    let labels = hml_unique(y);
    let n_classes = len(labels);
    let weights = {};
    let li = 0;
    while (li < n_classes) {
        let cnt = 0;
        let i = 0;
        while (i < n) {
            if (y[i] == labels[li]) { cnt = cnt + 1; }
            i = i + 1;
        }
        weights[labels[li]] = n * 1.0 / (n_classes * cnt);
        li = li + 1;
    }
    return weights;
}

# ── Compute Sample Weights ──

fn compute_sample_weights(y, class_weights) {
    let n = len(y);
    let weights = [];
    let i = 0;
    while (i < n) {
        let w = class_weights[y[i]];
        if (w == nullptr) { w = 1.0; }
        push(weights, w);
        i = i + 1;
    }
    return weights;
}

# ── Gaussian Noise Augmentation ──

fn gaussian_noise_augment(X, noise_std) {
    let n = len(X);
    let n_features = len(X[0]);
    let result = [];
    let i = 0;
    while (i < n) {
        let row = [];
        let j = 0;
        while (j < n_features) {
            let u1 = hml_random();
            let u2 = hml_random();
            let noise = math_sqrt(-2.0 * math_log(u1 + 0.0000001)) * math_cos(2.0 * 3.141592653589793 * u2) * noise_std;
            push(row, X[i][j] + noise);
            j = j + 1;
        }
        push(result, row);
        i = i + 1;
    }
    return result;
}

# ── Uniform Noise Augmentation ──

fn uniform_noise_augment(X, noise_range) {
    let n = len(X);
    let n_features = len(X[0]);
    let result = [];
    let i = 0;
    while (i < n) {
        let row = [];
        let j = 0;
        while (j < n_features) {
            let noise = (hml_random() - 0.5) * 2.0 * noise_range;
            push(row, X[i][j] + noise);
            j = j + 1;
        }
        push(result, row);
        i = i + 1;
    }
    return result;
}

# ── Mixup Augmentation ──

fn mixup_augment(X, y, alpha) {
    let n = len(X);
    let n_features = len(X[0]);
    let X_new = [];
    let y_new = [];
    let i = 0;
    while (i < n) {
        let j = hml_randint(0, n - 1);
        let lam = 0.0;
        if (alpha > 0.0) {
            let u = hml_random();
            if (u < 0.001) { u = 0.001; }
            lam = math_pow(u, 1.0 / alpha);
        } else {
            lam = hml_random();
        }
        let row = [];
        let f = 0;
        while (f < n_features) {
            push(row, lam * X[i][f] + (1.0 - lam) * X[j][f]);
            f = f + 1;
        }
        push(X_new, row);
        push(y_new, y[i]);
        i = i + 1;
    }
    return {"X": X_new, "y": y_new};
}

# ── CutMix Augmentation ──

fn cutmix_augment(X, y, alpha) {
    let n = len(X);
    let n_features = len(X[0]);
    let X_new = [];
    let y_new = [];
    let i = 0;
    while (i < n) {
        let j = hml_randint(0, n - 1);
        let lam = 0.0;
        if (alpha > 0.0) {
            let u = hml_random();
            if (u < 0.001) { u = 0.001; }
            lam = math_pow(u, 1.0 / alpha);
        } else {
            lam = hml_random();
        }
        let cut_start = hml_randint(0, n_features - 1);
        let cut_len = math_floor(lam * n_features);
        if (cut_len < 1) { cut_len = 1; }
        let cut_end = cut_start + cut_len;
        if (cut_end > n_features) { cut_end = n_features; }
        let row = [];
        let f = 0;
        while (f < n_features) {
            if (f >= cut_start and f < cut_end) {
                push(row, X[j][f]);
            } else {
                push(row, X[i][f]);
            }
            f = f + 1;
        }
        push(X_new, row);
        push(y_new, y[i]);
        i = i + 1;
    }
    return {"X": X_new, "y": y_new};
}

# ── Random Erasing ──

fn random_erasing(X, erase_ratio) {
    let n = len(X);
    let n_features = len(X[0]);
    let result = [];
    let i = 0;
    while (i < n) {
        let row = [];
        let f = 0;
        while (f < n_features) {
            push(row, X[i][f]);
            f = f + 1;
        }
        let erase_len = math_floor(n_features * erase_ratio);
        if (erase_len < 1) { erase_len = 1; }
        let start = hml_randint(0, n_features - erase_len);
        f = start;
        while (f < start + erase_len) {
            row[f] = 0.0;
            f = f + 1;
        }
        push(result, row);
        i = i + 1;
    }
    return result;
}
"""

# Now read the summary from the original file
summary_idx = summary_start
original_summary = '\n'.join(lines[summary_start:])

# Update the summary for v2.0
updated_summary = """# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY v2.0
# ═══════════════════════════════════════════════════════════════════════════
# H#ML — H# Machine Learning Library v2.0
# A comprehensive machine learning library implemented in pure H#.
#
# Sections:
#   1.  Random Number Generation  — LCG-based PRNG
#   2.  Vector Operations          — add, sub, scale, dot, norm, mean, argmax, argmin
#   3.  Matrix Operations          — multiply, transpose, add, sub, scale, zeros, ones
#   4.  Statistical Functions      — mean, std, var, column_means, unique, value_counts
#   5.  Basic Metrics              — accuracy, mse, mae, r2, confusion_matrix, train_test_split
#   6.  Advanced Metrics           — precision, recall, f1, roc_auc, silhouette, clustering metrics
#   7.  Loss Functions             — BCE, CCE, hinge, focal, huber, triplet, dice, wing, etc.
#   8.  Activation Functions       — sigmoid, tanh, relu, elu, selu, swish, gelu, mish, softmax
#   9.  Distance Metrics           — euclidean, manhattan, cosine, minkowski, haversine, edit distance
#  10.  Kernel Functions           — linear, polynomial, rbf, laplacian, histogram, spherical, etc.
#  11.  Preprocessing              — StandardScaler, MinMaxScaler, LabelEncoder
#  12.  Linear Regression          — gradient descent with MSE
#  13.  Logistic Regression        — sigmoid + binary cross-entropy
#  14.  KNN Classifier             — k-nearest neighbors with voting
#  15.  K-Means Clustering         — Lloyd's algorithm with random init
#  16.  Decision Tree Classifier   — CART with Gini impurity
#  17.  MLP Neural Network         — 1 hidden layer with ReLU activation
#  18.  Probability Distributions  — normal, uniform, gamma, beta, binomial, poisson, chi2, t, F, etc.
#  19.  Statistical Tests          — z-test, t-test, chi2, ANOVA, Kruskal-Wallis, KS, Shapiro-Wilk, etc.
#  20.  Feature Engineering        — polynomial, interaction, one-hot, binarize, quantile, power, k-bins, etc.
#  21.  Optimizers                 — SGD, Momentum, NAG, AdaGrad, RMSprop, Adam, AdaDelta, etc.
#  22.  Ensemble Models            — Voting, Bagging, AdaBoost, Gradient Boosting
#  23.  Cross Validation           — K-Fold, Stratified, Time Series, Grid/Random Search, Learning Curve
#  24.  Dimensionality Reduction   — PCA, SVD, LDA, Random Projection, Feature Agglomeration
#  25.  Data Augmentation          — SMOTE, Oversampling, Undersampling, Tomek Links, Noise, Mixup, CutMix
#  26.  Time Series Analysis       — moving avg, exponential smoothing, ARIMA, decomposition, stationarity
#  27.  NLP Basics                 — tokenization, stemming, lemmatization, TF-IDF, BLEU, ROUGE, WER
#  28.  Pipelines                  — Pipeline, FeatureUnion, ColumnTransformer, FunctionTransformer
#  29.  Outlier Detection          — Z-score, IQR, Isolation Forest, LOF, DBSCAN, Elliptic Envelope, OCSVM
#  30.  Missing Value Imputation   — forward fill, backward fill, linear, spline, mean, median, mode, KNN
#  31.  Model Persistence          — serialize/deserialize models to/from H# source code format
#
# Total: ~15,000+ lines of pure H# machine learning code.
# All algorithms implemented from scratch using only basic H# constructs.
# No external dependencies required.
# ═══════════════════════════════════════════════════════════════════════════"""

# Update the header
updated_header = """# ═══════════════════════════════════════════════════════════════════════════
# H#ML — H# Machine Learning Library v2.0
# ═══════════════════════════════════════════════════════════════════════════"""

# Replace the header in part1
part1_lines = part1.split('\n')
new_part1 = [updated_header] + part1_lines[5:]  # Replace first 5 lines (header)
part1 = '\n'.join(new_part1)

# Assemble the final file
final_content = part1 + '\n' + '\n' + extended + '\n' + '\n' + part3 + '\n' + '\n' + part4 + '\n' + '\n' + sec15 + '\n' + '\n' + sec16 + '\n' + '\n' + sec17 + '\n' + '\n' + sec18 + '\n' + '\n' + sections_19_24 + '\n' + '\n' + updated_summary

with open('bootstrap/hsharpmyl.hto', 'w') as f:
    f.write(final_content)

# Count lines
final_lines = final_content.split('\n')
print(f"Total lines: {len(final_lines)}")
print("Done!")