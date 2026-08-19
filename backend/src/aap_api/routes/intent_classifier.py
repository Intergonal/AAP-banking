from flask import Blueprint, jsonify, request
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
import kagglehub
from kagglehub import KaggleDatasetAdapter

intent_classifier = Blueprint(
    "intent_classifier", __name__, url_prefix="/api/intent-classifier"
)

# Loading the models
MODEL_HUB_PATH = "kristanlloyd/AAP-modernBERT-banking77"
print("Loading dataset label mappings...")
train_df = kagglehub.dataset_load(
    KaggleDatasetAdapter.PANDAS,
    "sssonnn/banking77",
    "train.csv",
)
mapping_df = train_df[['label', 'label_text']].drop_duplicates().sort_values('label')
id2label = {int(row['label']): str(row['label_text']) for _, row in mapping_df.iterrows()}
label2id = {v: k for k, v in id2label.items()}

print("Loading Intent Model from Hugging Face Hub...")
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_HUB_PATH,
    id2label=id2label,
    label2id=label2id
)
tokenizer = AutoTokenizer.from_pretrained(MODEL_HUB_PATH) 

intent_pipeline = pipeline("text-classification", model=model, tokenizer=tokenizer, top_k=3)

print("Loading Sentiment Model...")
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

print("All models loaded successfully!")


@intent_classifier.get("/health")
def health():
    return jsonify({"status": "ok", "service": "intent-classifier"})


@intent_classifier.post("/classify")
def classify():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    
    if not text.strip():
        return jsonify({"text": text, "intent": "unknown", "confidence": 0.0, "sentiment": "unknown"}), 400

    intent_results = intent_pipeline(text)[0] 
    top_intent = intent_results[0]['label']
    confidence = intent_results[0]['score']
    
    # Running the sentiment analyzer
    sentiment_results = sentiment_pipeline(text)
    sentiment = sentiment_results[0]['label']
    
    return jsonify({
        "text": text, 
        "intent": top_intent, 
        "confidence": confidence,
        "sentiment": sentiment,
        "full_intent_results": intent_results # Optional: pass the top 3 back just in case the frontend wants them
    })