########################################################################################
######################          Import packages      ###################################
########################################################################################
from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
import os

print(os.getcwd())
from init import create_app, db
import datetime

# [START gae_python38_auth_verify_token]
# [START gae_python3_auth_verify_token]
from flask import Flask, render_template, request

import pandas as pd
import torch
import json

from app_helpers import *


lstm_layer = torch.nn.LSTM(586, 128)


########################################################################################
# our main blueprint
main = Blueprint('main', __name__)

@main.route('/') # home page that return 'index'
def index():
    return render_template('index.html')

@main.route('/dashboard') # profile page that return 'profile'
@login_required
def dashboard():


    print("WORKING DIRECTORY: ", os.getcwd())


    # Read in census and migration data
    df = pd.read_csv(DATA_PATH)

    mig_6months = pd.read_csv(MONTH6_PATH)
    mig_12months = pd.read_csv(MONTH12_PATH)

    # print(df.head())

    # with open(MIGRATION_PATH) as m:
    #     mig_data = json.load(m)

    # # Get total # of migrants and a list of muni ID's
    # total_migrants = sum(list(mig_data.values()))
    # municipality_ids = list(mig_data.keys())

    # Calculate the average age of migrants per muni
    # df['avg_age_weight'] = df['avg_age'] * df['sum_num_intmig']
    # avg_age = df['avg_age_weight'].sum() / df['sum_num_intmig'].sum()

    # Open the variables JSON and the JSON containing the readable translation of the variables
    with open("./vars.json", "r") as f:
        grouped_vars = json.load(f)

    with open("./var_map.json", "r") as f2:
        var_names = json.load(f2)

    # print(grouped_vars)

    # Get all of the variables to send to Flask for dropdown options
    demog, family, edu, employ, hhold, crime = get_column_lists(df, var_names, grouped_vars)

    return render_template('profile.html', name=current_user.name,
                            demog_data = demog,
                            family_data = family,
                            edu_data = edu,
                            employ_data = employ,
                            hhold_data = hhold,
                            crime_data = crime,
                            month6_migs = "{:,}".format(int(mig_6months["serial"].sum())),
                            month12_migs = "{:,}".format(int(mig_12months["serial"].sum())))


@main.route('/geojson-features', methods=['GET'])
@login_required
def get_all_points():

    """
    Grabs the polygons from the geojson, converts them to JSON format with geometry and data 
    features and sends back to the webpage to render on the Leaflet map
    """

    print("here!!")

    # Convert the geoJSON to a dataframe and merge it to the migration data
    feature_df = convert_to_pandas(geodata_collection, MATCH_PATH, MONTH12_PATH)
    feature_df['sum_num_intmig'] = feature_df['serial'].fillna(0)
    feature_df['perc_migrants'] = feature_df['sum_num_intmig']# / feature_df['total_pop']
    
    print(feature_df)

    # Make lists of all of the features we want available to the Leaflet map
    coords = feature_df['geometry.coordinates']
    types = feature_df['geometry.type']
    num_migrants = feature_df['perc_migrants']
    shapeIDs = feature_df['shapeID']
    shapeNames = feature_df["properties.ipumns_simple_wgs_wdata_geo2_mx1960_2015_ADMIN_NAME"]

    # For each of the polygons in the data frame, append it and it's data to a list 
    # of dicts to be sent as a JSON back to the Leaflet map
    features = []
    for i in range(0, len(feature_df)):
        features.append({
            "type": "Feature",
            "geometry": {
                "type": types[i],
                "coordinates": coords[i]
            },
            "properties": {'num_migrants': num_migrants[i],
                           'shapeID': str(shapeIDs[i]),
                           'shapeName': shapeNames[i]
                          }
        })

    print("done up to here!!")


    response = jsonify(features)

    # Enable Access-Control-Allow-Origin
    response.headers.add("Access-Control-Allow-Origin", "*")        

    print("returning MAP!!")

    return response



@main.route('/predict_migration', methods=['GET', 'POST'])
def predict_migration():

    print(request.json)

    with open('status.json', 'w') as outfile:
        json.dump({'status': "Status - Starting predictions."}, outfile)

    mig12_months = pd.read_csv(MONTH12_PATH)
    mig6_months = pd.read_csv(MONTH6_PATH)


    # Parse the selected municipalities and get their unique B ID's
    selected_municipalities = request.json['selected_municipalities']

    print("LEN SELECTED MUNIS: ", len(selected_municipalities))

    # TEMPORARY UNTIL YOU GET THE BIG IMAGES DOWNLOADED
    selected_municipalities = [sm for sm in selected_municipalities if sm in munis_available]

    # Read in the migration data and subset it to the selected municipalities
    dta = pd.read_csv(MODEL_DATA_PATH)
    dta = dta.dropna(subset = ['muni_id'])

    dta_ids = dta["muni_id"].to_list()
    selected_municipalities = [sm for sm in selected_municipalities if int(sm) in dta_ids]

    print("IN DF: ", selected_municipalities)

    # If no muni's are selected, select them all
    if len(selected_municipalities) == 0:
        selected_municipalities = [str(i) for i in dta['GEO2_MX'].to_list()]
        selected_municipalities = [sm for sm in selected_municipalities if sm in munis_available]
        # selected_municipalities = [sm for sm in selected_municipalities if graph_id_dict[sm] not in BAD_IDS]
        print("Selected municipalities since none were selected: ", selected_municipalities)

    # print(dta.head())

    dta_selected, dta_dropped = prep_dataframes(dta, request, selected_municipalities)

    print("DTA SELECTED: ")
    print(dta_selected)

    predictions, preds_6months = [], []
    for muni in selected_municipalities:

        cur_dta = dta_selected[dta_selected["muni_id"] == int(muni)].fillna(0)

        cur_data_6month = cur_dta[cur_dta["month"].isin([7,8,9,10,11,12])].fillna(0)

        print("SIZES: ", cur_dta.shape, cur_data_6month.shape)

        cur_dta = np.array(cur_dta.drop(["muni_id", "year", "month", "migrants"], axis = 1).values, dtype = np.float32)
        cur_dta[cur_dta != cur_dta] = 0
        cur_dta = torch.tensor(cur_dta)


        cur_data_6month = np.array(cur_data_6month.drop(["muni_id", "year", "month", "migrants"], axis = 1).values, dtype = np.float32)
        cur_data_6month[cur_data_6month != cur_data_6month] = 0
        cur_data_6month = torch.tensor(cur_data_6month)


        if cur_dta.shape[0] == 12:
            predictions.append(model_12month(cur_dta).item())
        if cur_data_6month.shape[0] == 6:
            preds_6months.append(model_6month(cur_data_6month).item())
        else:
            predictions.append(mig12_months[mig12_months["muni_id"] == int(muni)]["serial"].values[0])
            preds_6months.append(mig6_months[mig6_months["muni_id"] == int(muni)]["serial"].values[0])
            # print("mig_12months: ", mig12_months)


        print(list(zip(predictions, preds_6months)))

        # print(cur_dta.shape)


    # #######################################################################
    # # Create some sort of dictionary with references to the graph_id_dict # 
    # #######################################################################
    # selected_muni_ref_dict = {}
    # for muni in selected_municipalities:
    #     muni_ref = graph_id_dict[muni]
    #     selected_muni_ref_dict[muni] = muni_ref

    # #######################################################################
    # # Create a dictionary with graph_id_dict                              #
    # # references mapped to the new census data                            #
    # #######################################################################
    # new_census_vals = {}
    # for sm in range(0, len(selected_municipalities)):
    #     new_census_vals[selected_muni_ref_dict[selected_municipalities[sm]]] = muns_to_pred[sm]

    #######################################################################
    # Predict the new data                                                # 
    #######################################################################
    # predictions = predict(graph, selected_muni_ref_dict, new_census_vals, selected_municipalities)

    #######################################################################
    # Update the new predictions in the dta_selected dataframe and append #
    # that to all of the data in dta_dropped that wan't selected to       #
    # create a full dataframe with everything                             #
    #######################################################################

    # 12 months
    mig12_months_selected = mig12_months[mig12_months['muni_id'].isin([int(i) for i in selected_municipalities])]
    mig12_months_nselected = mig12_months[~mig12_months['muni_id'].isin([int(i) for i in selected_municipalities])]

    # 6 months
    mig6_months_selected = mig6_months[mig6_months['muni_id'].isin([int(i) for i in selected_municipalities])]
    mig6_months_nselected = mig6_months[~mig6_months['muni_id'].isin([int(i) for i in selected_municipalities])]    


    print("6 MONTH SELECTED")
    print(mig6_months_selected.shape, len(preds_6months))


    # 12 months
    dta_selected = mig12_months_selected.rename(columns = {"serial": "migrants"})
    dta_selected['migrants'] = predictions
    dta_final = dta_selected.append(mig12_months_nselected.rename(columns = {"serial": "migrants"}))
    print("ALL DATA SHAPE: ", dta_final.shape)
    print("DTA FINAL HEAD: ", dta_final.head())


    # 6 months
    dta_selected_6month = mig6_months_selected.rename(columns = {"serial": "migrants"})
    dta_selected_6month['migrants'] = preds_6months
    dta_final_6month = dta_selected_6month.append(mig6_months_nselected.rename(columns = {"serial": "migrants"}))
    print("ALL DATA SHAPE: ", dta_final.shape)
    print("DTA FINAL 6 MONTH HEAD: ", dta_final_6month.head())


    #######################################################################
    # Normalize the geoJSON as a pandas dataframe and merge in the new    #
    # census & migration data                                             #
    #######################################################################
    dta_final['muni_id'] = dta_final['muni_id'].astype(str)
    dta_final[['muni_id', 'migrants']].to_csv(f"./map_layers/{current_user.name}_sum_num_intmig.csv", index = False)

    geoDF = json_normalize(geodata_collection["features"])
    merged = pd.merge(geoDF, dta_final, left_on = "properties.shapeID", right_on = "muni_id")
    merged['migrants'] = merged['migrants'].fillna(0)
    # merged['perc_migrants'] = merged['migrants'] / merged['total_pop']

    # dta_final['perc_migrants'] = dta_final['migrants'] / dta_final['total_pop']
    # dta_final[['muni_id', 'perc_migrants']].to_csv("./map_layers/perc_migrants.csv", index = False)

    og_df = pd.read_csv(MONTH12_PATH)
    og_df = og_df[['muni_id', 'serial']].rename(columns = {'serial': 'migrants_og'})
    og_df['muni_id'] = og_df['muni_id'].astype(str)
    change_df = pd.merge(og_df, dta_final[['muni_id', 'migrants']])
    change_df['absolute_change'] = change_df['migrants'] - change_df['migrants_og']
    change_df[['muni_id', 'absolute_change']].to_csv(f"./map_layers/{current_user.name}_absolute_change.csv", index = False)
    # change_df['perc_change'] = (change_df['migrants'] - change_df['migrants_og']) / change_df['sum_num_intmig_og']
    # change_df = change_df.replace([np.inf, -np.inf], np.nan)
    # change_df = change_df.fillna(0)
    # change_df[['muni_id', 'perc_change']].to_csv("./map_layers/perc_change.csv", index = False)

    #######################################################################
    # Aggregate statistics and send to a JSON                             #
    #######################################################################
    total_pred_migrants = merged['migrants'].sum()
    total_pred_migrants_6months = dta_final_6month['migrants'].sum()
    # merged['avg_age_weight'] = merged['avg_age'] * merged['sum_num_intmig']
    # avg_age = merged['avg_age_weight'].sum() / merged['sum_num_intmig'].sum()
    migration_statistics = {"total_pred_migrants": float(total_pred_migrants), "total_pred_migrants_6months": float(total_pred_migrants_6months)}
    with open(f"{current_user.name}_predicted_migrants.json", 'w') as outfile:
        json.dump(migration_statistics, outfile)

    #######################################################################
    # Convert features to a gejson for rendering in Leaflet               #
    #######################################################################
    features = convert_features_to_geojson(merged, column = 'migrants')

    with open('status.json', 'w') as outfile:
        json.dump({'status': "Status - Rendering new migration map..."}, outfile)

    print(current_user.name)

    return jsonify(features)





@main.route('/update_stats', methods=['GET'])
def update_stats():

    """
    Function used to update the statistc boxes at the top of the page & the graphs below the map
    """

    # Read in migration data
    df = pd.read_csv(MONTH12_PATH)
    df6 = pd.read_csv(MONTH6_PATH)


    with open(f"./{current_user.name}_predicted_migrants.json") as json_file:
        predictions = json.load(json_file)

    # Get the number of migrants (over a 5 year period) to send to HTML for stat box
    total_og_migrants = df['serial'].sum()
    total_pred_migrants = int(predictions['total_pred_migrants'])
    change = (total_pred_migrants - total_og_migrants)
    p_change = ( change / total_og_migrants ) * 100


    print("CHANGE: ", change)
    print("P CHANGE: ", p_change)
    

    # Get the number of migrants (over a 5 year period) to send to HTML for stat box
    total_og_migrants6 = df6['serial'].sum()
    total_pred_migrants6 = int(predictions['total_pred_migrants_6months'])
    change6 = (total_pred_migrants6 - total_og_migrants6)
    p_change6 = ( change6 / total_og_migrants6 ) * 100

    print("CHANGE 6: ", change6)
    print("P CHANGE 6: ", p_change6)
    
    # # Calculate average age stuff
    # df['avg_age_weight'] = df['avg_age'] * df['sum_num_intmig']
    # og_avg_age = df['avg_age_weight'].sum() / df['sum_num_intmig'].sum()

    # avg_age = predictions['avg_age']
    # avg_age_change = avg_age - og_avg_age
    # p_avg_age_change = ((round(avg_age, 2) - og_avg_age) / og_avg_age) * 100


    # with open("./correlations.json", "r") as f:
    #     corrs = json.load(f)

    # with open("./vars.json", "r") as f:
    #     var_cats = json.load(f)    

    # corr_means = []
    # corr_category_dict = {}
    # for category in var_cats.keys():
    #     cat_columns = var_cats[category]
    #     cat_vals = [round(abs(v), 4) for k,v in corrs.items() if k in cat_columns]
    #     if len(cat_vals) == 0:
    #         cat_mean_corr = 0
    #     else:
    #         cat_mean_corr = round(np.mean(cat_vals), 4)
    #         corr_category_dict[category] = [cat_columns, [round(v, 4) for k,v in corrs.items() if k in cat_columns]]
    #     corr_means.append(cat_mean_corr)
    #     print(category, cat_columns, cat_mean_corr)

    # migs_for_bs = pd.read_csv("./map_layers/sum_num_intmig.csv")
    # migs_for_bs = migs_for_bs["sum_num_intmig"].sum()

    # with open("./data/sector_fractions.json", "r") as f:
    #     bs_fractions = json.load(f)

    # for k,v in bs_fractions.items():
    #     bs_fractions[k] = bs_fractions[k] * migs_for_bs
    

    # changes = pd.read_csv("./map_layers/absolute_change.csv").sort_values(by = ["absolute_change"], ascending = False)
    # changes["GEO2_MX"] = changes["GEO2_MX"].astype(str)
    # with open("./data/shapeName_shapeID_dict.json", "r") as f:
    #     id_map = json.load(f)
    # changes["GEO2_MX"] = changes["GEO2_MX"].astype(str).map(id_map)
    # top_munis = changes["GEO2_MX"].to_list()[0:10]
    # top_changes = changes["absolute_change"].round(2).to_list()[0:10]

    # bottom_munis = changes["GEO2_MX"].to_list()[-10:][::-1]
    # bottom_changes = changes["absolute_change"].round(2).to_list()[-10:][::-1]


    return {'change': int(change),
            'p_change': round(p_change, 2),
            'predicted_migrants': round(total_pred_migrants, 0),
            'change6': int(change6),
            'p_change6': round(p_change6, 2),
            'predicted_migrants6': round(total_pred_migrants6, 0)}


    # return {'change': int(change),
    #         'p_change': round(p_change, 2),
    #         'predicted_migrants': round(total_pred_migrants / 5, 0),
    #         'avg_age': round(avg_age, 0),
    #         'avg_age_change': round(avg_age_change, 0),
    #         'pavg_age_change': round(p_avg_age_change, 0),
    #         'corr_means': corr_means,
    #         'corr_category_dict': corr_category_dict,
    #         'bs_fractions_labels': list(bs_fractions.keys()),
    #         'bs_fractions_values': list(bs_fractions.values()),
    #         'model_error': f'{int((round(total_pred_migrants, 0) / 5) * MODEL_ERROR):,}',
    #         'top_munis': top_munis,
    #         'top_changes': top_changes,
    #         'bottom_munis': bottom_munis,
    #         'bottom_changes': bottom_changes,
    #         }




@main.route('/var_drilldown', methods=['GET', 'POST'])
def var_drilldown():

    """
    Function to return data for the variable drilldown sidebar
    """

    # Save the requested variable
    info_var = request.json['info_var']

    # Read in impact CSV
    df = pd.read_csv(IMPACT_PATH)

    # Get the underscored version of the variable name
    with open("./var_map.json", "r") as f:
        var_names = json.load(f)
    for k,v in var_names.items():
        if v == info_var:
            mapped_name = k
            break

    print("here!!")

    # Get the category and list of other category variables of the variable
    with open("./vars.json", "r") as f2:
        var_cats = json.load(f2)
    for k in var_cats.keys():
        if mapped_name in var_cats[k]:
            var_cat = k
            cat_vars = var_cats[k]
            break

    # Get the variable's rank
    var_rank = df[df['var'] == mapped_name]['rank'].values[0]

    # Get cateogry, rank and impact data on the variable
    cat_df = df[df['var'].isin(cat_vars)]
    cat_df = cat_df.sort_values(by = "impact", ascending = False)
    cat_df['rank'] = [i for i in range(len(cat_df))]
    var_cat_rank = cat_df[cat_df['var'] == mapped_name]['rank'].values[0]
    var_quant = cat_df[cat_df['var'] == mapped_name]['quant'].values[0]

    try:

        # Get ALE data on the variable
        ale_df = pd.read_csv(ALE_PATH)
        ale = list(ale_df[mapped_name].values)
        ale = [round(i / 5, 0) for i in ale]

        with open(ALE_INTERVALS_PATH, "r") as ale_i:
            ale_i = json.load(ale_i)

        ale_labels = [" to ".join(i) for i in ale_i[mapped_name]]

    except:

        print("FAILED AT VARIABLE: ", mapped_name)

        mapped_name = 'INDIG'

        # Get ALE data on the variable
        ale_df = pd.read_csv(ALE_PATH)
        ale = list(ale_df[mapped_name].values)
        ale = [round(i / 5, 0) for i in ale]

        with open(ALE_INTERVALS_PATH, "r") as ale_i:
            ale_i = json.load(ale_i)

        ale_labels = [" to ".join(i) for i in ale_i[mapped_name]]

    print("ALE: ", ale)

    # ale = [i if i is not ]

    
    # Send back to server
    return {'var_rank': str(var_rank + 1),
            'num_vars': str(len(list(var_names.keys()))),
            'var_cat_rank': str(var_cat_rank + 1),
            'num_cat_vars': str(len(cat_df)),
            'quant': var_quant,
            'ale_values': ale,
            'ale_labels': ale_labels,
            }




app = create_app() # we initialize our flask app using the __init__.py function
if __name__ == '__main__':
    db.create_all(app=create_app()) # create the SQLite database
    app.run(debug = True) # run the flask app on debug mode