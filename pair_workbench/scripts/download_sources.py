"""Download public source files with pinned SHA-256; does not execute remote content."""
import argparse, hashlib, shutil, urllib.request
from pathlib import Path
from prepare_datasets import EXPECTED_HASHES

PREFIX='https://raw.githubusercontent.com/cltl/ecbPlus/master/ECB%2B_LREC2014/'
URLS={
    'ecbplus/ECB+.zip': PREFIX+'ECB%2B.zip',
    'ecbplus/ECBplus_coreference_sentences.csv': PREFIX+'ECBplus_coreference_sentences.csv',
    'tkgqa/new_sentence_df_0509.csv': 'https://osf.io/download/y65b9/',
    'tkgqa/sentence_df_articleId_to_url.csv': 'https://osf.io/download/swrn9/',
}
HASHES={**EXPECTED_HASHES, 'ecbplus/ECBplus_coreference_sentences.csv': 'fe065a6a03d7c9e27a9947a3de327381dca06bf3a4d3eb38fb59df526da9b1bb'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--destination',type=Path,default=Path('local_data/raw'))
    args=parser.parse_args()
    for relative,url in URLS.items():
        target=args.destination/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            temporary=target.with_suffix(target.suffix+'.part')
            print('Downloading',relative,flush=True)
            with urllib.request.urlopen(url,timeout=120) as response,temporary.open('wb') as output:
                shutil.copyfileobj(response,output)
            actual=hashlib.sha256(temporary.read_bytes()).hexdigest()
            if actual!=HASHES[relative]:
                raise ValueError('Source hash changed: '+relative+'; inspect .part file before continuing')
            temporary.replace(target)
        if hashlib.sha256(target.read_bytes()).hexdigest()!=HASHES[relative]:
            raise ValueError('Existing source hash mismatch: '+relative)
        print('Verified',relative)
    notices=Path(__file__).resolve().parents[1]/'data/pilot/licenses/ecbplus'
    for name in ('LICENSEDATA.TXT','COPYING-CC.TXT','SOURCE_README.txt'):
        shutil.copy2(notices/name,args.destination/'ecbplus'/name)
    print('Sources ready:',args.destination.resolve())

if __name__=='__main__': main()
