# -*- coding: utf-8 -*-
"""Implied_Volatility_Surface.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11G6K4n1X43bn6wFjWDJNaQ5Kd8MWNtRx
"""

from google.colab import drive
drive.mount('/content/drive')

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import feature_column
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from pandas import read_csv
from pandas import DataFrame
from pandas import concat
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from numpy import concatenate
from math import sqrt
from matplotlib import pyplot 

np.set_printoptions(precision=3, suppress=True)
pd.options.display.max_rows = 10
pd.options.display.float_format = "{:.1f}".format
tf.keras.backend.set_floatx('float32')

print("Imported the modules.")

def Data_Prep(df,df_len,conv_tenor=True,pos_chang=True,final_df=True,add_col=True):

  if conv_tenor:

    val_mon=[]
    for i in range(df_len):
      int_val=int(df['Tenor'][i][:-1])
      if df['Tenor'][i][-1]=="M":
        val_mon.append(str(int_val*1))
      elif df['Tenor'][i][-1]=="Y":
        val_mon.append(str(int_val*12))
    df['Tenor_mon']=val_mon

  if add_col:

    df['Date'] = pd.to_datetime(df['Date'])
    df['day_of_week'] = df['Date'].dt.day
    df['year'] = df['Date'].dt.year
    df['month'] = df['Date'].dt.month
    df['exp_date']='2017-01-05'
    df['exp_date']=pd.to_datetime(df['exp_date'])
    for i in range(df_len):
      df['exp_date'][i]=df.Date[i] + pd.DateOffset(months=int(df.Tenor_mon[i]))   
    df['Tenor_days'] = df['Date'] - df['exp_date']
    df['Tenor_days']=abs(df['Tenor_days']/np.timedelta64(1,'D'))
    df['Tenor_days'] = df["Tenor_days"].astype("int64")
    
  if pos_chang:

    df1 = df.stack().reset_index(-1).iloc[:, ::-1]
    df1.columns = ['IV', 'Strike_price']
    rem=['Date','Tenor','Tenor_days','Tenor_mon','day_of_week','year','month','exp_date']
    df1 = df1[df1.Strike_price.isin(rem) == False]
  
  if final_df:
    
    df_new=pd.concat([df['Date'],df['day_of_week'],df['month'],df['year'],df['Tenor'], df['Tenor_days'],df['Tenor_mon'],df['exp_date'],df1['Strike_price'],df1['IV']], axis=1)
    df_new['Date_num']=tf.convert_to_tensor(df_new.Date.values.astype(np.int64))
    df_new["Date_num"] /= 1000000000000
    df_new.reset_index(inplace=True)
    df_new = df_new.rename(columns = {'index':'Deadline_count'})
    df_new.drop(['Tenor_mon'], axis=1, inplace=True)

  return df_new

df=pd.read_csv('/content/drive/MyDrive/Problem_Statement/data/training_data.csv',sep=",")

df.describe(include='all',datetime_is_numeric=True)

df=Data_Prep(df,len(df.index),conv_tenor=True,pos_chang=True,final_df=True,add_col=True)
df

ind=pd.concat([df['Deadline_count']],axis=1)
ind

df_n=df[['day_of_week','month','year','Tenor_days','Strike_price','Date_num','IV']]
np.asarray(df_n.values).astype('float32')
df_n

def Plot_to_comp(df):
	values = df.values
	groups = [0, 1, 2, 3,4, 5, 6]
	i = 1
	pyplot.figure()
	for group in groups:
		pyplot.subplot(len(groups), 1, i)
		pyplot.plot(values[:, group])
		pyplot.title(df.columns[group], y=0.5, loc='right')
		i += 1
	pyplot.show()

Plot_to_comp(df_n)

df_n.to_csv('IVS_Cleaned_Data.csv')

dataset = read_csv('IVS_Cleaned_Data.csv', header=0, index_col=0)
dataset

def spliter(df):

  train_main_df, test_df = train_test_split(df, test_size=0.2,shuffle=False)
  train_df, val_df = train_test_split(train_main_df, test_size=0.2,shuffle=False)

  train=train_df.values
  Val=val_df.values
  test=test_df.values

  train_X, train_y = train[:, :-1], train[:, -1]
  Val_X, Val_y = Val[:, :-1], Val[:, -1]
  test_X, test_y = test[:, :-1], test[:, -1]

  train_X = train_X.reshape((train_X.shape[0], 1, train_X.shape[1]))
  Val_X = Val_X.reshape((Val_X.shape[0], 1, Val_X.shape[1]))
  test_X = test_X.reshape((test_X.shape[0], 1, test_X.shape[1]))

  print(train_X.shape, train_y.shape, Val_X.shape, Val_y.shape, test_X.shape, test_y.shape)

  return train_df,val_df,test_df,train_X,train_y,Val_X,Val_y,test_X,test_y

train_df,val_df,test_df,train_X,train_y,Val_X,Val_y,test_X,test_y=spliter(dataset)

def create_model(df):

  model = tf.keras.Sequential([
  layers.Conv1D(filters=32, kernel_size=3, strides=1, padding="causal", activation="relu", input_shape=(df.shape[1], df.shape[2])),
  layers.LSTM(256,return_sequences=True),
  layers.Dense(128, activation='relu'),
  layers.LSTM(124,activation='relu'),
  layers.Dense(64, activation='relu'),
  layers.Dropout(0.25),
  layers.Dense(128, activation='relu',kernel_regularizer=tf.keras.regularizers.l1(l=0.003)),
  layers.Dense(64),
  layers.Dropout(0.25),
  layers.Dense(1),
  ])

  model.compile(loss="mean_squared_error",optimizer=tf.keras.optimizers.Adam(learning_rate=0.03,beta_1=0.9))

  return model

model_fin=create_model(train_X)

model_fin.summary()

hist = model_fin.fit(train_X, train_y, epochs=99, batch_size=100, validation_data=(Val_X, Val_y), verbose=1, shuffle=False)

def loss_plot(his):
  pyplot.plot(his.history['loss'], label='train')
  pyplot.plot(his.history['val_loss'], label='test')
  pyplot.legend()
  pyplot.show()

loss_plot(hist)

model_fin.save('./IVS_tf',save_format='tf')
!zip -r IVS_HACK.zip {'./IVS_tf'}

!unzip /content/IVS_HACK.zip -d /content/
model_fin = tf.keras.models.load_model('./IVS_tf')

yhat = model_fin.predict(test_X)

test_X = test_X.reshape((test_X.shape[0], test_X.shape[2]))
inv_yhat = concatenate((yhat, test_X[:, 0:]), axis=1)
inv_yhat = inv_yhat[:,0]

test_y = test_y.reshape((len(test_y), 1))
inv_y = concatenate((test_y, test_X[:, 0:]), axis=1)
inv_y = inv_y[:,0]

rmse = sqrt(mean_squared_error(inv_y, inv_yhat))
print('Test RMSE: %.3f' % rmse)

x = concatenate((yhat, test_X[:, 4:5]), axis=1)
x=DataFrame(x)
x=x.iloc[:,::-1]
recovered_df = x.pivot_table(index = ind.Deadline_count, columns = 1,values = 0)
recovered_df.columns.name = None  
recovered_df.index.name=None
recovered_df

df1=pd.read_csv('/content/drive/MyDrive/Problem_Statement/data/training_data.csv',sep=",")

a,b=train_test_split(df1,test_size=0.2,shuffle=False)
b=b.reset_index(drop=True)
final=pd.concat([b['Date'],b['Tenor'],recovered_df],axis=1)
final=final.fillna(0)
final.to_csv('prediction_template.csv')

predict= read_csv('prediction_template.csv', header=0, index_col=0)
predict