"""
ChromaDB vector database manager
"""
import chromadb
from chromadb.config import Settings
import uuid
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ChromaManager:
    """Manage ChromaDB vector database operations"""
    
    def __init__(self, persist_directory: str = "chromadb_data", collection_name: str = "job_documents"):
        """
        Initialize ChromaDB manager
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection to use
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        try:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(allow_reset=True, anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}  # Cosine similarity
            )
            
            logger.info(f"ChromaDB initialized. Collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            self.client = None
            self.collection = None
    
    def add_job_document(self, job_data: Dict) -> bool:
        """
        Add a job document to ChromaDB
        
        Args:
            job_data: Dictionary with job information
            
        Returns:
            bool: Success status
        """
        if not self.collection:
            logger.error("ChromaDB collection not initialized")
            return False
        
        try:
            # Create document content
            document_content = self._create_document_content(job_data)
            
            # Create metadata
            metadata = self._create_metadata(job_data)
            
            # Generate document ID
            doc_id = job_data.get('job_id', str(uuid.uuid4()))
            if not doc_id:
                doc_id = str(uuid.uuid4())
            
            # Add to ChromaDB
            self.collection.add(
                documents=[document_content],
                metadatas=[metadata],
                ids=[f"job_{doc_id}"]
            )
            
            logger.debug(f"Added job to ChromaDB: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding job document to ChromaDB: {e}")
            return False
    
    def _create_document_content(self, job_data: Dict) -> str:
        """Create document content for vectorization"""
        parts = []
        
        if job_data.get('title'):
            parts.append(f"Title: {job_data['title']}")
        
        if job_data.get('work_mode'):
            parts.append(f"Work Mode: {job_data['work_mode']}")
        
        if job_data.get('experience_certs'):
            parts.append(f"Experience/Certifications: {job_data['experience_certs']}")
        
        if job_data.get('skills_full'):
            parts.append("Skills:")
            for skill in job_data['skills_full']:
                parts.append(f"  - {skill}")
        
        if job_data.get('description'):
            parts.append(f"Description: {job_data['description']}")
        
        if job_data.get('location'):
            parts.append(f"Location: {job_data['location']}")
        
        return "\n".join(parts)
    
    def _create_metadata(self, job_data: Dict) -> Dict:
        """Create metadata for document"""
        metadata = {
            'job_id': str(job_data.get('job_id', '')),
            'title': str(job_data.get('title', '')),
            'state': str(job_data.get('state', '')),
            'work_mode': str(job_data.get('work_mode', '')),
            'source_file': str(job_data.get('source_file', '')),
            'document_type': 'job_requisition',
            'has_skills': 'true' if job_data.get('skills_full') else 'false',
            'has_description': 'true' if job_data.get('description') else 'false'
        }
        
        # Add skills as searchable metadata
        if job_data.get('skills_clean'):
            skills_list = [str(skill) for skill in job_data['skills_clean'][:10] if skill]
            metadata['skills'] = '|'.join(skills_list) if skills_list else ''
        else:
            metadata['skills'] = ''
        
        return metadata
    
    def search_similar_jobs(self, query: str, n_results: int = 10, 
                           filter_conditions: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar jobs using semantic search
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_conditions: Optional filters
            
        Returns:
            List of search results
        """
        if not self.collection:
            logger.error("ChromaDB collection not initialized")
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_conditions,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity_score': 1.0 - results['distances'][0][i],
                        'source': 'vector_search'
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get ChromaDB collection statistics"""
        if not self.collection:
            return {'error': 'ChromaDB not initialized'}
        
        try:
            count = self.collection.count()
            return {
                'collection_name': self.collection_name,
                'total_documents': count,
                'status': 'active',
                'embeddings_model': 'all-MiniLM-L6-v2'  # Default ChromaDB model
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}