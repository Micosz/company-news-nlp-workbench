"""Exploratory Pilot NLI graph ablation. Not CohTP. No test-label access."""
import json
from pathlib import Path
import numpy as np

def run(train, test, config):
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    from sklearn.feature_extraction.text import TfidfVectorizer
    if len(train)+len(test)>1000:
        raise ValueError('NLI graph pilot supports at most 1000 pairs. Select Pilot A or B.')
    if config.get('threshold_mode','fixed')!='fixed':
        raise ValueError('Graph pilot currently requires fixed threshold 0.5.')
    torch.set_num_threads(2)
    seed=int(config.get('seed',374)); torch.manual_seed(seed)
    model_id='cross-encoder/nli-deberta-v3-small'
    tokenizer=AutoTokenizer.from_pretrained(model_id)
    nli=AutoModelForSequenceClassification.from_pretrained(model_id).eval()
    revision=getattr(nli.config,'_commit_hash',None)
    corpus=list(dict.fromkeys(train.text_a.tolist()+train.text_b.tolist()))
    vec=TfidfVectorizer(max_features=256).fit(corpus)
    def graph(frame):
        texts=list(dict.fromkeys(frame.text_a.tolist()+frame.text_b.tolist()))
        lookup={t:i for i,t in enumerate(texts)}
        pairs=torch.tensor([[lookup[a],lookup[b]] for a,b in zip(frame.text_a,frame.text_b)])
        probs=[]
        for start in range(0,len(frame),8):
            batch=frame.iloc[start:start+8]; a=batch.text_a.tolist(); b=batch.text_b.tolist()
            encoded=tokenizer(a+b,b+a,padding=True,truncation=True,max_length=256,return_tensors='pt')
            with torch.no_grad(): p=nli(**encoded).logits.softmax(-1)
            probs.append((p[:len(a)]+p[len(a):])/2)
        edge=torch.cat(probs)
        # Published model mapping: contradiction=0, entailment=1, neutral=2.
        adj=torch.eye(len(texts))
        for (a,b),p in zip(pairs,edge): adj[a,b]=adj[b,a]=p[1]
        adj=adj/adj.sum(1,keepdim=True)
        x=torch.tensor(vec.transform(texts).toarray(),dtype=torch.float32)
        return x,adj,pairs,edge,texts
    tr=graph(train); te=graph(test)
    class PairNet(torch.nn.Module):
        def __init__(self, message):
            super().__init__(); self.message=message
            self.encoder=torch.nn.Linear(len(vec.vocabulary_),32)
            self.head=torch.nn.Sequential(torch.nn.Linear(67,32),torch.nn.ReLU(),torch.nn.Linear(32,1))
        def forward(self,g):
            x,adj,pairs,edge,_=g
            h=torch.relu(self.encoder(adj@x if self.message else x))
            a,b=h[pairs[:,0]],h[pairs[:,1]]
            return self.head(torch.cat([abs(a-b),a*b,edge],1)).ravel()
    y=torch.tensor(train.label.to_numpy(dtype=float),dtype=torch.float32)
    models={}; graph_scores={}
    for name,message in [('nli_no_graph',False),('nli_gnn',True)]:
        torch.manual_seed(seed); net=PairNet(message); opt=torch.optim.Adam(net.parameters(),lr=.01)
        for epoch in range(80):
            opt.zero_grad(); loss=torch.nn.functional.binary_cross_entropy_with_logits(net(tr),y); loss.backward(); opt.step()
        net.eval()
        with torch.no_grad(): scores=net(te).sigmoid().tolist()
        models[name]={'scores':scores,'threshold':.5,'features':['tfidf_nodes','bidirectional_nli']+(['weighted_message_passing'] if message else [])}
        graph_scores[name]=scores
        torch.save(net.state_dict(),Path(__file__).parent/(name+'.pt'))
    x,adj,pairs,edge,texts=te
    payload={'nodes':[{'id':i,'text':t} for i,t in enumerate(texts)],'edges':[{'a':int(p[0]),'b':int(p[1]),'nli':e.tolist(),'score':graph_scores['nli_gnn'][i]} for i,(p,e) in enumerate(zip(pairs,edge))], 'model':model_id,'revision':revision}
    (Path(__file__).parent/'graph.json').write_text(json.dumps(payload))
    return {'models':models,'method':'Frozen bidirectional NLI; train-only TF-IDF node features; weighted one-layer message passing versus matched no-message model; 80 epochs; CPU; threshold 0.5.','warnings':['Exploratory Pilot only, not CohTP. No claim of improvement from a single seed.','Train/test graphs separate. Test graph uses unlabeled test texts jointly; candidate edges are supplied dataset pairs.','Nodes merge identical context strings; these are text nodes, not guaranteed distinct event mentions.','NLI scores are not coreference labels. Entailment weights messages; contradiction is only a pair feature.','English pretrained model; contexts truncated to 256 tokens. Model training overlap with evaluation sources is unverified.'], 'vectorizer':{'vocabulary':{k:int(v) for k,v in vec.vocabulary_.items()},'model_id':model_id,'revision':revision,'epochs':80,'seed':seed}}
