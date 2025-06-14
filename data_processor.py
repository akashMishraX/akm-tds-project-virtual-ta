import os
import json
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter,MarkdownHeaderTextSplitter
from langchain.docstore.document import Document
from typing import List,Dict,Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from langchain.embeddings import OpenAIEmbeddings
from urllib.parse import urlparse
import hashlib


class TDSDataProcessor:
    def __init__(self):
        # Initialize splitters with optimal settings
        self.markdown_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
                ("####", "Header 4")
            ]
        )
        self.discourse_quote_re = re.compile(r'^\[quote=.*?\].*?\[\/quote\]\s*',  re.DOTALL | re.MULTILINE)
        self.mention_re = re.compile(r'@\w+\b')
        self.url_re = re.compile(r'https?://\S+|www\.\S+')
        self.code_block_re = re.compile(r'```.*?```', re.DOTALL)
        self.whitespace_re = re.compile(r'\s+')
        self.empty_line_re = re.compile(r'\n\s*\n')
    
    def load_markdown_content(self, metadata_file: str, markdown_dir: str) -> List[Dict]:
        """Load and combine markdown files with their metadata"""
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        documents = []
        
        for item in metadata:
            filepath = os.path.join(markdown_dir, item['filename'])
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Extract front matter if exists
                    front_matter = {}
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            front_matter_str = parts[1]
                            content = parts[2]
                            
                            for line in front_matter_str.split('\n'):
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    front_matter[key.strip()] = value.strip().strip('"')
                    
                    # Combine metadata sources
                    combined_metadata = {
                        **item,
                        **front_matter,
                        'source': 'course_content',
                        'content_type': 'course_material'
                    }
                    
                    documents.append({
                        'content': content,
                        'metadata': combined_metadata
                    })
        
        return documents
    def clean_text(self, text: str, is_discourse: bool = False) -> str:
        """Clean text content based on source"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = BeautifulSoup(text, 'html.parser').get_text()
        
        # Discourse-specific cleaning
        if is_discourse:
            text = self.discourse_quote_re.sub('', text)
            text = self.mention_re.sub('', text)
            text = self.code_block_re.sub('[code]', text)
        
        # General cleaning
        text = self.url_re.sub('', text)
        text = self.whitespace_re.sub(' ', text)
        text = self.empty_line_re.sub('\n\n', text)
        
        return text.strip()
    
    def process_course_content(self, documents: List[Dict]) -> List[Document]:
        """Process course markdown content into chunks"""
        processed_docs = []
        
        for doc in documents:
            content = doc['content']
            metadata = doc['metadata']
            
            try:
                # First split by headers
                header_splits = self.header_splitter.split_text(content)
                
                for split in header_splits:
                    # Then split by chunk size if needed
                    chunks = self.markdown_splitter.split_documents([split])
                    
                    for chunk in chunks:
                        # Create document with combined metadata
                        final_metadata = {
                            **metadata,
                            **chunk.metadata,
                            'doc_id': hashlib.md5(chunk.page_content.encode()).hexdigest()
                        }
                        
                        processed_docs.append(Document(
                            page_content=self.clean_text(chunk.page_content),
                            metadata=final_metadata
                        ))
                        
            except Exception as e:
                print(f"Error processing {metadata.get('filename')}: {str(e)}")
                # Fallback to simple splitting
                chunks = self.markdown_splitter.create_documents(
                    [self.clean_text(content)],
                    [metadata]
                )
                processed_docs.extend(chunks)
        
        return processed_docs
    
    def process_discourse_posts(self, input_file: str) -> List[Document]:
        """Process Discourse JSON data into chunks"""
        with open(input_file, 'r', encoding='utf-8') as f:
            posts = json.load(f)
        
        processed_docs = []
        
        for post in posts:
            content = self.clean_text(post.get('content', ''), is_discourse=True)
            if not content or len(content) < 25:  # Skip very short posts
                continue
                
            # Create metadata
            metadata = {
                'source': 'discourse',
                'url': post.get('url', ''),
                'author': post.get('author', 'Anonymous'),
                'created_at': post.get('created_at', ''),
                'updated_at': post.get('updated_at', ''),
                'topic_id': post.get('topic_id', ''),
                'post_id': post.get('post_id', ''),
                'topic_title': post.get('topic_title', ''),
                'is_accepted_answer': post.get('is_accepted_answer', False),
                'reply_count': post.get('reply_count', 0),
                'like_count': post.get('like_count', 0),
                'tags': post.get('tags', []),
                'post_type': 'answer' if post.get('is_reply') else 'question',
                'doc_id': hashlib.md5(content.encode()).hexdigest()
            }
            
            # Split content into chunks if needed
            chunks = self.markdown_splitter.create_documents(
                [content],
                [metadata]
            )
            
            processed_docs.extend(chunks)
        
        return processed_docs
    def enhance_metadata(self, documents: List[Document]) -> List[Document]:
        """Add derived metadata and quality scoring"""
        for doc in documents:
            # Add domain from URL
            if 'url' in doc.metadata:
                parsed = urlparse(doc.metadata['url'])
                doc.metadata['domain'] = parsed.netloc
            
            # Different quality scoring for course vs discourse
            if doc.metadata['source'] == 'course_content':
                doc.metadata['quality_score'] = 1.0  # Highest priority for course content
                doc.metadata['content_type'] = 'course_material'
            else:
                # Discourse quality scoring
                score = 0.5  # Base score
                if doc.metadata.get('is_accepted_answer'):
                    score += 0.3
                score += min(0.2, doc.metadata.get('like_count', 0) / 50)
                score += min(0.1, doc.metadata.get('reply_count', 0) / 20)
                doc.metadata['quality_score'] = round(score, 2)
                
                # Classify discourse content
                if '[code]' in doc.page_content.lower():
                    doc.metadata['content_type'] = 'code_' + doc.metadata['post_type']
                else:
                    doc.metadata['content_type'] = 'text_' + doc.metadata['post_type']
        
        return documents
    
    def filter_by_date(self, documents: List[Document], 
                      date_from: str, 
                      date_to: str) -> List[Document]:
        """Filter documents by date range (ISO format strings)"""
        if not date_from or not date_to:
            return documents
            
        date_from = datetime.fromisoformat(date_from)
        date_to = datetime.fromisoformat(date_to)
        filtered = []
        
        for doc in documents:
            created_at = doc.metadata.get('created_at')
            if not created_at:
                continue
                
            try:
                post_date = datetime.strptime(
                    created_at, 
                    "%Y-%m-%dT%H:%M:%S.%fZ"
                )
            except ValueError:
                try:
                    post_date = datetime.strptime(
                        created_at, 
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                except:
                    continue
            
            if date_from <= post_date <= date_to:
                filtered.append(doc)
        
        return filtered
    
    def save_processed_data(self, 
                          documents: List[Document], 
                          output_file: str,
                          min_quality: float = 0.0):
        """Save processed documents to JSON file"""
        serializable = []
        
        for doc in documents:
            if doc.metadata.get('quality_score', 0) >= min_quality:
                serializable.append({
                    'page_content': doc.page_content,
                    'metadata': doc.metadata
                })
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Saved {len(serializable)} documents to {output_file}")
    
    def run_pipeline(self, config: Dict):
        """Complete processing pipeline"""
        print("🚀 Starting TDS data processing pipeline...")
        
        # Process course content if configured
        course_docs = []
        if 'markdown_metadata' in config and 'markdown_dir' in config:
            print("📚 Processing course markdown content...")
            markdown_content = self.load_markdown_content(
                config['markdown_metadata'],
                config['markdown_dir']
            )
            course_docs = self.process_course_content(markdown_content)
            print(f"  Processed {len(course_docs)} course content chunks")
        
        # Process discourse posts if configured
        discourse_docs = []
        if 'discourse_input' in config:
            print("💬 Processing Discourse posts...")
            discourse_docs = self.process_discourse_posts(config['discourse_input'])
            
            # Apply date filtering if specified
            if 'date_from' in config and 'date_to' in config:
                discourse_docs = self.filter_by_date(
                    discourse_docs,
                    config['date_from'],
                    config['date_to']
                )
            print(f"  Processed {len(discourse_docs)} Discourse posts")
        
        # Combine and enhance all documents
        all_docs = course_docs + discourse_docs
        print(f"🔗 Combining {len(all_docs)} total documents...")
        enhanced_docs = self.enhance_metadata(all_docs)
        
        # Save results
        self.save_processed_data(
            enhanced_docs,
            config.get('output_file', 'processed_data/tds_processed.json'),
            min_quality=config.get('min_quality', 0.0)
        )
        
        print("🎉 Data processing complete!")
    
if __name__ == "__main__":
    # Example configuration matching your data
    config = {
        "markdown_metadata": "metadata.json",
        "markdown_dir": "markdown_files",
        "discourse_input": "discourse_posts.json",
        "date_from": "2025-01-01",
        "date_to": "2025-04-14",
        "output_file": "processed_data/tds_combined.json",
        "min_quality": 0.3
    }
    
    processor = TDSDataProcessor()
    processor.run_pipeline(config)

