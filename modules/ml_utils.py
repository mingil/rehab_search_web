import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from pyvis.network import Network
import networkx as nx
from modules.logger_setup import logger

def perform_topic_clustering(df):
    df_copy = df.copy()
    valid_idx = df_copy[df_copy['Abstract'].str.len() > 20].index
    if len(valid_idx) < 10:
        df_copy['Topic_Cluster'] = "General Topic"
        return df_copy
    texts = (df_copy.loc[valid_idx, 'Title'] + " " + df_copy.loc[valid_idx, 'Abstract']).tolist()
    try:
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        X = vectorizer.fit_transform(texts)
        n_clusters = max(2, min(4, len(valid_idx) // 4))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
        clusters = kmeans.fit_predict(X)
        order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
        terms = vectorizer.get_feature_names_out()
        cluster_names = {}
        for i in range(n_clusters):
            top_words = [terms[ind] for ind in order_centroids[i, :3]]
            cluster_names[i] = f"[{', '.join(top_words).title()}]"
        df_copy['Topic_Cluster'] = "Unclassified"
        df_copy.loc[valid_idx, 'Topic_Cluster'] = [cluster_names[c] for c in clusters]
        pca = PCA(n_components=3, random_state=42)
        coords = pca.fit_transform(X.toarray())
        df_copy.loc[valid_idx, 'PCA_x'], df_copy.loc[valid_idx, 'PCA_y'], df_copy.loc[valid_idx, 'PCA_z'] = coords[:, 0], coords[:, 1], coords[:, 2]
    except Exception as e:
        logger.error(f"ML Clustering Error: {e}")
        df_copy['Topic_Cluster'] = "General Topic"
    return df_copy

def generate_network_graph(df):
    try:
        net = Network(height='450px', width='100%', bgcolor='#ffffff', font_color='#111111', cdn_resources='remote')
        G = nx.Graph()
        for _, r in df.head(30).iterrows():
            title_node = str(r['Title'])[:30] + "..."
            journal_node = str(r['Journal'])
            cluster_node = str(r.get('Topic_Cluster', 'General Topic'))
            G.add_node(title_node, title=str(r['Title']), group=1, size=15, color="#1565C0")
            G.add_node(journal_node, title=journal_node, group=2, size=25, color="#E53935")
            G.add_node(cluster_node, title=cluster_node, group=3, size=30, color="#43A047")
            G.add_edge(title_node, journal_node, color="#E0E0E0")
            G.add_edge(title_node, cluster_node, color="#E0E0E0")
        net.from_nx(G)
        return net.generate_html()
    except Exception as e:
        logger.error(f"NetworkX Error: {e}")
        return ""
