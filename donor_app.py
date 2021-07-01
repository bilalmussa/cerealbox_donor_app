# -*- coding: utf-8 -*-
"""
Created on Fri Jun 18 14:11:01 2021

@author: bmussa
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import RendererAgg
import seaborn as sns
import matplotlib
from matplotlib.figure import Figure
import base64
from io import BytesIO
import smtplib

def get_table_download_link_csv(df, message):
    csv = df.to_csv(index=False).encode('utf-8-sig')
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="'+ df.name +'.csv" target="_blank">' + message +'</a>'
    return href

st.set_page_config(layout="wide")

matplotlib.use("agg")

_lock = RendererAgg.lock

sns.set_style('white')

row0_spacer1, row0_1, row0_spacer2, row0_2, row0_spacer3 = st.beta_columns(
    (.1, 2, .2, 2, .1))

row0_1.title('Analyse your donor data')
#row0_1.write('')

row1_spacer1, row1_1, row1_spacer2 = st.beta_columns((.1, 30, .1))

with row1_1:
    st.markdown("Welcome to CerealBox Quick Analysis app. We just need 4 columns from your donor data for (ideally) the last 3 years, and the app will automaically profile your donors and will display various statistics and charts for your analysis.")
    st.markdown("The system reads the data, analyses it, and displays the results. No data is stored during the process.")
 
row2_spacer1, row2_1, row2_spacer2 = st.beta_columns((.1, 30, .1))
with row2_1:
    st.write("We accept the data in a CSV format with the following column headers:")
    st.write("- OrderDateTime: Date and Time of the donation in DD/MM/YYYY format")
    st.write("- ItemCost: Donation amount in a number format")
    st.write("- CustomerID: Unique ID of the donor - can be email address or donor key")
    st.write("- OrderID: Unique ID of the donation - can be text or numeric or mixed")

example_dict = {'OrderDateTime': ['31/05/2021','29/05/2021','05/05/2021'],
                'ItemCost': [5.6,7.7,10],
                'CustomerID': [1111,222222,333333],
                'OrderID' : ['abc1', 'efg3', 'hij4']
                }

example_data = pd.DataFrame(example_dict)
example_data.name = 'example_data'

row3_spacer1, row3_1, row3_spacer2 = st.beta_columns((.1, 30, .1))
with row3_1:
    example_data
    st.markdown(get_table_download_link_csv(example_data,"Click here to download a sample CSV template"), unsafe_allow_html=True)
    st.markdown("The app is preloaded with the above example data")

@st.cache
def tidy_data(data):
    #clean up some of the data where needed
    data['OrderDate'] = pd.to_datetime(data['OrderDateTime']).dt.date
    #fill blank order IDs with 1
    data['OrderID'] = data['OrderID'].replace('nan', np.nan).fillna(1)
    data['ItemCost'] = pd.to_numeric(data['ItemCost'],errors='coerce')
    return data


row4_spacer1, row4_1, row4_spacer2 = st.beta_columns((.1, 30, .1))
with row4_1:
    user_input = st.file_uploader("Upload CSV",type=['csv'])

row5_spacer1, row5_1, row5_spacer2 = st.beta_columns((.1, 30, .1))
with row5_1:
    # Create a text element and let the reader know the data is loading.
    if not user_input:
        trans_data = tidy_data(example_data)
    else:
        data_load_state = st.text('Waiting to load data...')
        trans_data = tidy_data(pd.read_csv(user_input,parse_dates=['OrderDateTime'], dayfirst=True))        
        # Notify the reader that the data was successfully loaded.
        data_load_state.text('Loading data...done!')

#get max date from data series
max_date = trans_data['OrderDate'].max()
last_year = (datetime.strptime(str(trans_data['OrderDate'].max()),"%Y-%m-%d")+ timedelta(days=-365)).date()
last_year_1 = (datetime.strptime(str(trans_data['OrderDate'].max()),"%Y-%m-%d")+ timedelta(days=-730)).date()

row6_spacer1, row6_1, row6_spacer2 = st.beta_columns((.1, 30, .1))
with row6_1:
    exp_raw_data = st.beta_expander(label='View Raw Data')
    with exp_raw_data:
        st.subheader('Raw data')
        st.write(trans_data)
    exp_stats = st.beta_expander(label='View Statistics')
    with exp_stats:
        st.subheader('Data stats')
        st.write('There are ', len(trans_data), ' records in the data where you have ', trans_data['CustomerID'].nunique(), ' donors. The latest donation date is', max_date, 'Below is a summary of the data - item cost field only.')
        data_description = trans_data['ItemCost'].agg(['count','mean', 'sum', 'min', 'max','median']).reset_index()
        st.write(data_description)

#%% select data from transdata for last 12 months on

@st.cache
def data_calcs(trans_data):
    last12data = trans_data[trans_data['OrderDate']>=last_year]
    #%% add months columns to last 12 monts
    last12data['months'] = pd.to_datetime(trans_data['OrderDate']).dt.strftime('%Y-%m')
    #%% pivot the data out and fill with 1 or 0
    last12months_pivot = pd.pivot_table(data = last12data, values='OrderID', index='CustomerID', columns='months', aggfunc='count')
    last12months_pivot = last12months_pivot.replace('nan', np.nan).fillna(0)
    #%% code it up so that there is only 1 or 0
    list_of_cols = list(last12months_pivot.columns)
    last12months_pivot= pd.DataFrame(last12months_pivot)
    for col in list_of_cols:
        last12months_pivot[col] = last12months_pivot[col].apply(lambda x: 1 if x>0 else 0).astype(np.uint8)
        #%% create aggregated dataset
    agg_data = trans_data.groupby(['CustomerID']).agg({'ItemCost': ['sum']
                                                      ,'OrderID': ['count']
                                                      ,'OrderDate': ['min','max']}
                                                      ).reset_index()
    
    agg_data.columns = ['CustomerID', 'TotalDonationValue', 'TotalDonations', 'FirstDonation','LastDonation']
    
    agg_data['ATV'] = agg_data['TotalDonationValue']/agg_data['TotalDonations']
    
    agg_data['AvgTimePDonation'] = ((agg_data['LastDonation'] -agg_data['FirstDonation'])/np.timedelta64(1,'D'))/agg_data['TotalDonations']
    
    #agg_data[agg_data['FirstDonation'].between(last_year, max_date)]
        
    condlist = [(agg_data.FirstDonation>=last_year),            
                (agg_data.LastDonation>=last_year)&(agg_data.FirstDonation<last_year_1),
                (agg_data.FirstDonation<last_year)&(agg_data.LastDonation>=last_year),
                (agg_data.LastDonation<last_year)
                ]
    
    choicelist = ['New'
                  , 'Reactivated'
                  , 'Active'
                  ,'Lapsed']
    
    agg_data['CustStatus'] = np.select(condlist, choicelist, default='unknown')
    
    condlist = [(agg_data.AvgTimePDonation<=7),            
                (agg_data.AvgTimePDonation<=30),
                (agg_data.AvgTimePDonation<=180),
                (agg_data.AvgTimePDonation<=365),
                (agg_data.AvgTimePDonation>365),
                ]
    
    choicelist = ['1. Weekly'
                  , '2. Monthly'
                  ,'3. Bi Annually'
                  , '4. Annually'
                  , '5. More than a year']
    
    agg_data['AvgTimePDonationBand'] = np.select(condlist, choicelist, default='unknown')
    
    condlist = [(agg_data.ATV<20),            
                (agg_data.ATV<50),
                (agg_data.ATV<=100),
                (agg_data.ATV<=250),
                (agg_data.ATV<=500),
                (agg_data.ATV>500),
                ]
    
    choicelist = ['1. < £20'
                  , '2. £20 - £50'
                  , '3. £50 - £100'
                  , '4. £100 - £250'
                  , '5. £250 - £500'
                  , '6. £500+']
    
    agg_data['ATVBand'] = np.select(condlist, choicelist, default='unknown')
    
    condlist = [(agg_data.TotalDonationValue<50),            
                (agg_data.TotalDonationValue<100),
                (agg_data.TotalDonationValue<200),
                (agg_data.TotalDonationValue<500),
                (agg_data.TotalDonationValue<1000),
                ]
    
    choicelist = ['1. < £50'
                  , '2. £50 - £100'
                  , '3. £100 - £200'
                  , '4. £200 - £500'
                  , '5. £500 - £1000']
    
    agg_data['TotalDonationValueBand'] = np.select(condlist, choicelist, default='6. More than £1000')
    
    #%%merge last 12 month pivot onto aggregated data set
    
    agg_data = pd.merge(agg_data, last12months_pivot, how='left', left_on='CustomerID', right_on='CustomerID')
    
    #%% last 12 months spend
    
    last12data_spend = last12data.groupby(last12data['CustomerID']).agg({'ItemCost': ['sum']}).reset_index()
    
    last12data_spend.columns = ['CustomerID', 'Spend12m']
    
    #%% last12m spend back onto merged df
    agg_data = agg_data.merge(last12data_spend,how='left', on='CustomerID')
    
    #%% months spent
    agg_data['monthsSpent'] = agg_data[list_of_cols].sum(axis=1)
    
    #%% loyalty band
    
    agg_data['monthsSpent'] = agg_data['monthsSpent'].replace('nan', np.nan).fillna(0)
    
    condlist = [(agg_data.CustStatus=='New'),
                (agg_data.monthsSpent>9),            
                (agg_data.monthsSpent>3),
                ((agg_data.monthsSpent<=3) & (agg_data.monthsSpent>0)),
                ]
    
    choicelist = ['0. New Customer'
                  ,'1. High Loyal'
                  , '2. Med Loyal'
                  , '3. Low Loyal'
                  ]
    
    agg_data['LoyaltyBand'] = np.select(condlist, choicelist, default='4. No Spender')
    
    #%% create column for last 12m spend
    condlist = [(agg_data.Spend12m<250),            
                (agg_data.Spend12m<1000),
                (agg_data.Spend12m>1000),            
                ]
    
    choicelist = ['1. < £250'
                  , '2. £250 - £1000'
                  , '3. >£1000'
                  ]
    
    agg_data['Last12mDonationValueBand'] = np.select(condlist, choicelist, default='7. No Spender')
    return agg_data

agg_data = data_calcs(trans_data)

#%% charts for analysis
row7_spacer1, row7_1,row7_spacer2 = st.beta_columns((.1, 30, .1))
with row7_1, _lock:
    exp_data_cuts = st.beta_expander(label='View Data Cuts')
    with exp_data_cuts:
        option = st.selectbox(
         'Which field would you like to cut the data by?',
         ('LoyaltyBand', 'TotalDonationValueBand', 'CustStatus','Last12mDonationValueBand','AvgTimePDonationBand','ATVBand'))
        st.write('You selected:', option)
        data_cut = agg_data[agg_data['CustomerID']!=0]
        data_cut = agg_data.groupby([option]).agg({'CustomerID': ['count']
                                                   ,'TotalDonationValue': ['sum']
                                                   ,'TotalDonations': ['sum']
                                                   ,'Spend12m': ['sum']
                                                   }).sort_index().reset_index()
        data_cut.columns = [option
                            , 'Counts'
                            ,'Total Donation Value'
                            , 'Total Donations'
                            , 'Total Donation Value Last12m'
                            ]
    
        data_cut['Avg Donor Value']= data_cut['Total Donation Value']/data_cut['Counts']
        data_cut['Avg Donations']= data_cut['Total Donations']/data_cut['Counts']
        data_cut['Avg Donor Value Last12m']= data_cut['Total Donation Value Last12m']/data_cut['Counts']
        data_cut['ATV']= data_cut['Total Donation Value']/data_cut['Total Donations']
        data_cut = data_cut.round({'Counts': 0
                                   , 'Total Donation Value': 2
                                   , 'Total Donations': 0
                                   , 'Total Donation Value Last12m': 2
                                   , 'Avg Donor Value': 2
                                   , 'Avg Donations': 2
                                   , 'Avg Donor Value Last12m': 2
                                   , 'ATV': 2
                                   })
        st.dataframe(data_cut,width=1600)

exp_charts = st.beta_expander(label='View Charts')
with exp_charts:
    row9_spacer1, row9_1, row9_2, row9_spacer2 = st.beta_columns((.1, 3.2,3.2, 0.1))       
    with row9_1, _lock:
        st.subheader('Count of donors by '+ option)
        fig = Figure()
        ax = fig.subplots()
        sns.barplot(data = data_cut, x = data_cut[option], y=data_cut['Counts'],
                    color="goldenrod", ax=ax)
        ax.set_ylabel('Counts')
        ax.set_xlabel(option)
        ax.label_outer()
        for item in ax.get_xticklabels():
            item.set_rotation(45)
        st.pyplot(fig)
    with row9_2, _lock:
        st.subheader('Total Donation Value of donors by '+ option)
        fig = Figure()
        ax = fig.subplots()
        sns.barplot(data = data_cut, x = data_cut[option], y=data_cut['Total Donation Value'],
                    color="goldenrod", ax=ax)
        ax.set_ylabel('Total Donation Value')
        ax.set_xlabel(option)
        for item in ax.get_xticklabels():
            item.set_rotation(45)
        st.pyplot(fig)
    
    st.write('')
    
    row10_spacer1, row10_1,row10_2, row10_spacer2 = st.beta_columns((.1, 3.2,3.2, 0.1))
    with row10_1, _lock:
        st.subheader('Total Donations of donors by '+ option)
        fig = Figure()
        ax = fig.subplots()
        sns.barplot(data = data_cut, x = data_cut[option], y=data_cut['Total Donations'],
                    color="goldenrod", ax=ax)
        ax.set_ylabel('Total Donations')
        ax.set_xlabel(option)
        for item in ax.get_xticklabels():
            item.set_rotation(45)
        st.pyplot(fig)
    with row10_2, _lock:
        st.subheader('Avg Number of Donations by '+ option)
        fig = Figure()
        ax = fig.subplots()
        sns.barplot(data = data_cut, x = data_cut[option], y=data_cut['Avg Donations'],
                    color="goldenrod", ax=ax)
        ax.set_ylabel('Avg Donations')
        ax.set_xlabel(option)
        for item in ax.get_xticklabels():
            item.set_rotation(45)
        st.pyplot(fig)
    
    st.write('')
    
    row11_spacer1, row11_1,row11_2, row11_spacer2 = st.beta_columns((.1, 3.2,3.2, 0.1))
    with row11_1, _lock:
        st.subheader('Avg Donor Value of donors by '+ option)
        fig = Figure()
        ax = fig.subplots()
        sns.barplot(data = data_cut, x = data_cut[option], y=data_cut['Avg Donor Value'],
                    color="goldenrod", ax=ax)
        ax.set_ylabel('Avg Donor Value')
        ax.set_xlabel(option)
        for item in ax.get_xticklabels():
            item.set_rotation(45)
        st.pyplot(fig)
    with row11_2, _lock:
        st.subheader('Total Donation Value of donors by '+ option)
        fig = Figure()
        ax = fig.subplots()
        sns.barplot(data = data_cut, x = data_cut[option], y=data_cut['Total Donation Value Last12m'],
                    color="goldenrod", ax=ax)
        ax.set_ylabel('Total Donation Value')
        ax.set_xlabel(option)
        for item in ax.get_xticklabels():
            item.set_rotation(45)
        st.pyplot(fig)
    
    st.write('')
    
    row12_spacer1, row12_1,row12_2, row12_spacer2 = st.beta_columns((.1, 3.2,3.2, 0.1))
    with row12_1, _lock:
        st.subheader('ATV of donors by '+ option)
        fig = Figure()
        ax = fig.subplots()
        sns.barplot(data = data_cut, x = data_cut[option], y=data_cut['ATV'],
                    color="goldenrod", ax=ax)
        ax.set_ylabel('ATV')
        ax.set_xlabel(option)
        for item in ax.get_xticklabels():
            item.set_rotation(45)
        st.pyplot(fig)
    with row12_2, _lock:
        st.subheader('Avg Donor Value Last12m of donors by '+ option)
        fig = Figure()
        ax = fig.subplots()
        sns.barplot(data = data_cut, x = data_cut[option], y=data_cut['Avg Donor Value Last12m'],
                    color="goldenrod", ax=ax)
        ax.set_ylabel('Avg Donor Value Last12m')
        ax.set_xlabel(option)
        for item in ax.get_xticklabels():
            item.set_rotation(45)
        st.pyplot(fig)
    
    st.write('') 
    
 
#%% auto generated insights

exp_charts = st.beta_expander(label='View Insights')
with exp_charts:
    row13_spacer1, row13_1, row13_spacer2 = st.beta_columns((0.1, 3.2, .1))
    with row13_1:
        st.subheader('Based on the data we suggest the following...')
        if agg_data[agg_data['LastDonation']>=last_year_1].count()[0]>0:
            count = agg_data[agg_data['LastDonation']>=last_year_1].count()[0]
            st.write('Create a Look-A-Like audience using your ', count, ' donors to reach a new larger yet relevant audience.')

        if agg_data[agg_data['CustStatus']=='Lapsed'].count()[0]>0:
            count = agg_data[agg_data['CustStatus']=='Lapsed'].count()[0]
            st.write('Reach out to your ', count, ' Lapsed donors to get them to donate again. Heavily retargeting them via Social Media Ads to increase top of mind awareness but also to drive conversions.')

        if agg_data[(agg_data['CustStatus']=='New') & (agg_data['TotalDonations']==1)].count()[0]>0:
            count = agg_data[(agg_data['CustStatus']=='New') & (agg_data['TotalDonations']==1)].count()[0]
            total_spend = agg_data[(agg_data['CustStatus']=='New') & (agg_data['TotalDonations']==1)]['ATV'].sum()               
            st.write('Encourage ', count, ' new donors that have donated once to donated again.','This could be worth upto ', round(total_spend,0))           

#        if agg_data[(agg_data['LoyaltyBand']=='3. Low Loyal')].count()[0]>0:
#            count = agg_data[(agg_data['LoyaltyBand']=='3. Low Loyal')].count()[0]
#            st.write(count, ' don't donate frequently. Develop a regular giving campaign to covert these one-off donors into regular givers.')
#
#        if agg_data[(agg_data['CustStatus']=='Reactivated')].count()[0]>0:
#            count = agg_data[(agg_data['CustStatus']=='Reactivated')].count()[0]
#            st.write('Send a thank you note to ', count, ' customers that have come back after a 12 months break')
#
#        if agg_data[(agg_data['TotalDonations']==2)].count()[0]>0:
#            count = agg_data[(agg_data['TotalDonations']==2)].count()[0]
#            total_spend = agg_data[(agg_data['TotalDonations']==2)]['ATV'].sum()               
#            st.write('The ',count, 'customers that have transacted twice, transact just once more then that will yield upto', round(total_spend,0))
#
#        if (agg_data[(agg_data['ATV']>=18) & (agg_data['ATVBand']=='1. < £20')].count()[0]>0
#        or agg_data[(agg_data['ATV']>=45) & (agg_data['ATVBand']=='2. £20 - £50')].count()[0]>0
#        or agg_data[(agg_data['ATV']>=90) & (agg_data['ATVBand']=='3. £50 - £100')].count()[0]>0
#        or agg_data[(agg_data['ATV']>=225) & (agg_data['ATVBand']=='4. £100 - £250')].count()[0]>0
#        or agg_data[(agg_data['ATV']>=450) & (agg_data['ATVBand']=='5. £250 - £500')].count()[0]>0):
#            count = agg_data[(agg_data['ATV']>=18) & (agg_data['ATVBand']=='1. < £20')].count()[0]
#            count += agg_data[(agg_data['ATV']>=45) & (agg_data['ATVBand']=='2. £20 - £50')].count()[0]
#            count += agg_data[(agg_data['ATV']>=90) & (agg_data['ATVBand']=='3. £50 - £100')].count()[0]
#            count += agg_data[(agg_data['ATV']>=225) & (agg_data['ATVBand']=='4. £100 - £250')].count()[0]
#            count += agg_data[(agg_data['ATV']>=450) & (agg_data['ATVBand']=='5. £250 - £500')].count()[0]
#            st.write('Split test avg txn amount on ', count, 'customers that could be ready to move up a band')      

#%% final aggregated dataset

row13_spacer1, row13_1, row13_spacer2 = st.beta_columns((0.1, 30 , .1))
with row13_1:
    exp_agg_data = st.beta_expander(label='View Aggregated Data Set')
    with exp_agg_data :
        st.subheader('Aggregated data')
        st.write(agg_data)


#%% download file

agg_data.name = 'agg_data'

st.markdown(get_table_download_link_csv(agg_data,"Download aggregated data as a csv file"), unsafe_allow_html=True)

#%% send your details over
st.subheader("Let's connect and go through your data")
with st.form(key='my_form'):
    text_input = st.text_input(label='Enter your name')
    text_input2 = st.text_input(label='Enter your email address')    
    submit_button = st.form_submit_button(label='Submit')
    
    if submit_button==1 and text_input=="" and text_input2=="":
        st.write('Please enter your name & email address')
    elif submit_button==1 and text_input=="":
        st.write('Please enter your name')
    elif submit_button==1 and text_input2=="":
        st.write('Please enter your email address') 
    
    if submit_button==1 and text_input!="" and text_input2!="":
        fromaddr = text_input2
        toaddrs  = st.secrets["db_username"]
        msg = 'You have a new enquiry'
        username = st.secrets["db_username"]
        password = st.secrets["db_password"]
        msg = "\r\n".join([
          "From:"+ fromaddr ,
          "To:" + toaddrs ,
          "Subject: New enquiry from: " + fromaddr,
          "",
          "Name: " + text_input ,
          "",
          "Email: " + text_input2
          ])
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        server.login(username,password)
        server.sendmail(fromaddr, toaddrs, msg)
        server.quit()
        st.write('Thank you for your email. We will be in touch shortly.')
