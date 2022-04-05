from flask import render_template, request, json, jsonify
from app import app
from werkzeug.utils import secure_filename
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
import os
import csv
import server as sv

DATASETLOC      = 'static/file/dataset/'
PREPOCESSINGLOC = 'static/file/preprocessing/'
TESTLOC         = 'static/file/testing/'

ALLOWED_EXTENSION = {'csv'}

def set_default(obj):
    if isinstance(obj, set):
        return list(obj)        # turn object containing set to list so JSON can handle it
    raise TypeError

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSION

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/preprosessing', methods=['POST', 'GET'])
def preprosessing():
    if request.method == 'POST':
        file = request.files['dataset']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(DATASETLOC, filename))
        else:
            return jsonify(message='error'), 500

        loc     = os.path.join(DATASETLOC, filename)
        review  = sv.LoadData.readData(loc)

        review['clean']      = review['reviews'].apply(sv.Preprocessing.cleaning)
        print("----------------------------------------")
        print("-------------CLEANING DONE--------------")
        review['normalized'] = review['clean'].apply(sv.Preprocessing.normalisasi)
        print("----------------------------------------")
        print("-----------NORMALIZATION DONE-----------")
        review['swremoved']  = review['normalized'].apply(sv.Preprocessing.stopwords_removal)
        print("----------------------------------------")
        print("---------STOPWORDS REMOVAL DONE---------")

        factory     = StemmerFactory()
        stemmer     = factory.create_stemmer()

        term_dict   = {}

        for document in review['swremoved']:
            for term in document:
                if term not in term_dict:
                    term_dict[term] = ' '
       
        for term in term_dict:
            term_dict[term] = stemmer.stem(term)
            print(term,":" ,term_dict[term])

        print(term_dict)
        print("----------------------------------------")
        print("--------------STEMMING DONE-------------")
        print("----------------------------------------")

        def get_stemmed_term(document):
                return [term_dict[term] for term in document]

        review['stemmed'] = review['swremoved'].apply(get_stemmed_term)
        review['wrapped'] = review['stemmed'].apply(sv.Preprocessing.gabung)
        review['review']  = review['label'] + ' ' + review['wrapped']

        filename    = 'preprocessed_'+filename
        prepLoc     = sv.LoadData.saveData(PREPOCESSINGLOC, review['review'], filename)
        hasil       = {"message": f"{file.filename} has been cleaned..", "hPrep": {prepLoc}}
        res         = json.dumps(hasil, default=set_default), 200
        return res
    return render_template('index.html')

@app.route('/training', methods=['POST', 'GET'])
def training():
    if request.method == 'POST':
        file = request.files['dataTrain']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(PREPOCESSINGLOC, filename))
        else:
            return jsonify(message='error'), 500

        loc     = os.path.join(PREPOCESSINGLOC, filename)
        mess    = sv.Fasttext.train(loc)
        res     = {"pesan" : {mess}}
        data    = json.dumps(res, default=set_default), 200
        return data
    return render_template('index.html')


@app.route("/testing", methods=["GET", "POST"])
def testing():
    if request.method == "POST":

        file = request.files["dataTest"]

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(TESTLOC, filename))
        else:
            return jsonify(message='error'), 500

        loc_test    = os.path.join(TESTLOC, filename)
        test_df     = sv.LoadData.readData(loc_test)
        model       = sv.Fasttext.loadmodel('finalized_model.bin')

        def predict(df):
            return model.predict(df['review'])

        test_df['prediction'] = test_df.apply(predict,axis=1) # axis 1 = row, axis 0 = column
        filename    = 'tested_'+filename
        sv.LoadData.saveData(TESTLOC, test_df, filename)
        predictions = sv.Fasttext.test(loc_test, model)
        hasil       = {"result": {predictions}, "file"  : f"{filename}"}
        res         = json.dumps(hasil, default=set_default), 200
        return (res)
    return render_template('index.html')


@app.route('/predictsentence', methods=['GET', 'POST'])
def predict_sentence():
    if request.method == 'POST':
        sentence    = request.form['dataPredictText']
        prediction  = sv.Fasttext.predict_sentence(sentence)
        label       = prediction[0]
        accur       = prediction[1]
        hasil       = {"prediction" : {label}, "accuracy"   : f"{accur}"}
        res         = json.dumps(hasil, default=set_default), 200
        return res
    return render_template('index.html')


@app.route("/preprocessres", methods=["GET"])
def show_prep_res():
    data = []
    with open(PREPOCESSINGLOC + 'preprocessed_datatrial.csv') as csvfile:
        data_csv = csv.DictReader(csvfile, delimiter=',')
        for row in data_csv:
            data.append(dict(row))
    data = {"data": data}
    return jsonify(data)


@app.route("/testres/<file>", methods=["GET"])
def show_test_res(file):
    print(file)
    data = []
    with open(TESTLOC + file) as csvfile:
        data_csv = csv.DictReader(csvfile, delimiter=',')
        for row in data_csv:
            data.append(dict(row))
    data = {"data": data}
    return jsonify(data)
