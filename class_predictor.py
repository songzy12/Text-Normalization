import pandas as pd
import numpy as np
import os
import gc
import xgboost as xgb
import re
from sklearn.model_selection import train_test_split

INPUT_DIR = "./input/"
OUTPUT_DIR = "./output/"


max_num_features = 10
pad_size = 1
boundary_letter = -1
space_letter = 0
max_data_size = 320  # 320000

df = pd.read_csv(INPUT_DIR+'en_train.csv', encoding='utf8')

x_data = []
y_data = pd.factorize(df['class'])
labels = y_data[1]
y_data = y_data[0]
gc.collect()
for x in df['before'].values:
    x_row = np.ones(max_num_features, dtype=int) * space_letter
    for xi, i in zip(list(str(x)), np.arange(max_num_features)):
        x_row[i] = ord(xi)
    x_data.append(x_row)

df_test = pd.read_csv(INPUT_DIR+'en_test_2.csv', encoding='utf8')
x_test = []
for x in df_test['before'].values:
    x_row = np.ones(max_num_features, dtype=int) * space_letter
    for xi, i in zip(list(str(x)), np.arange(max_num_features)):
        x_row[i] = ord(xi)
    x_test.append(x_row)


def context_window_transform(data, pad_size):
    pre = np.zeros(max_num_features)
    pre = [pre for x in np.arange(pad_size)]
    data = pre + data + pre
    neo_data = []
    for i in np.arange(len(data) - pad_size * 2):
        row = []
        for x in data[i: i + pad_size * 2 + 1]:
            row.append([boundary_letter])
            row.append(x)
        row.append([boundary_letter])
        neo_data.append([int(x) for y in row for x in y])
    return neo_data


x_data = x_data[:max_data_size]
y_data = y_data[:max_data_size]
x_data = np.array(context_window_transform(x_data, pad_size))
gc.collect()
x_data = np.array(x_data)
y_data = np.array(y_data)


x_test = x_test[:max_data_size]
x_test = np.array(context_window_transform(x_test, pad_size))
x_test = np.array(x_test)

print('Total number of samples:', len(x_data))
print('Use: ', max_data_size)
print('Total number of test samples:', len(x_test))

print('x_data sample:')
print(x_data[0])
print('y_data sample:')
print(y_data[0])
print('labels:')
print(labels)

x_train = x_data
y_train = y_data
gc.collect()

x_train, x_valid, y_train, y_valid = train_test_split(
    x_train, y_train, test_size=0.1, random_state=2017)
gc.collect()
num_class = len(labels)
dtrain = xgb.DMatrix(x_train, label=y_train)
dvalid = xgb.DMatrix(x_valid, label=y_valid)
watchlist = [(dvalid, 'valid'), (dtrain, 'train')]

dtest = xgb.DMatrix(x_test)

param = {'objective': 'multi:softmax',
         'eta': '0.3', 'max_depth': 10,
         'silent': 1, 'nthread': -1,
         'num_class': num_class,
         'eval_metric': 'merror'}
model = xgb.train(param, dtrain, 50, watchlist, early_stopping_rounds=20,
                  verbose_eval=10)
gc.collect()

pred = model.predict(dvalid)
pred = [labels[int(x)] for x in pred]
y_valid = [labels[x] for x in y_valid]
x_valid = [[chr(x) for x in y[2 + max_num_features: 2 +
                              max_num_features * 2]] for y in x_valid]
x_valid = [''.join(x) for x in x_valid]
x_valid = [re.sub('a+$', '', x) for x in x_valid]

pred_test = model.predict(dtest)
pred_test = [labels[int(x)] for x in pred_test]
x_test = [[chr(x) for x in y[2 + max_num_features: 2 +
                             max_num_features * 2]] for y in x_test]
x_test = [''.join(x) for x in x_test]
x_test = [re.sub('a+$', '', x) for x in x_test]

gc.collect()

df_pred = pd.DataFrame(columns=['data', 'predict', 'target'])
df_pred['data'] = x_valid
df_pred['predict'] = pred
df_pred['target'] = y_valid
df_pred.to_csv(os.path.join(OUTPUT_DIR, 'pred_valid.csv'), encoding='utf8')

df_pred_test = pd.DataFrame(columns=['data', 'predict'])
df_pred_test['data'] = x_test
df_pred_test['predict'] = pred_test
df_pred_test.to_csv(os.path.join(
    OUTPUT_DIR, 'pred_test.csv'), encoding='utf8')

model.save_model(os.path.join(OUTPUT_DIR, 'model.json'))
