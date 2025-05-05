"""Tests for the AI processor module."""

import pytest
from unittest.mock import patch, MagicMock

from newsletter_generator.ai.processor import (
    AIProcessor,
    get_ai_processor,
    categorise_content,
    summarise_content,
    generate_insights,
    evaluate_relevance,
    generate_newsletter_section,
)


@pytest.fixture
def ai_processor():
    """Create an AI processor for testing."""
    with patch("newsletter_generator.ai.processor.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        processor = AIProcessor()
        
        yield processor


class TestAIProcessor:
    """Test cases for the AIProcessor class."""
    
    def test_init(self):
        """Test initialising the AI processor."""
        with patch("newsletter_generator.ai.processor.OpenAI") as mock_openai:
            processor = AIProcessor()
            
            mock_openai.assert_called_once()
            assert processor.llm_model == "o4-mini"
    
    def test_categorise_content(self, ai_processor):
        """Test categorising content."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = """
        {
            "primary_category": "Machine Learning",
            "secondary_categories": ["Artificial Intelligence", "Data Science"],
            "tags": ["neural networks", "deep learning", "tensorflow", "pytorch", "transformers"],
            "confidence": 0.95
        }
        """
        
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        ai_processor.openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_processor.categorise_content("Test content about machine learning")
        
        assert result["primary_category"] == "Machine Learning"
        assert "Artificial Intelligence" in result["secondary_categories"]
        assert "neural networks" in result["tags"]
        assert result["confidence"] == 0.95
        
        ai_processor.openai_client.chat.completions.create.assert_called_once()
    
    def test_categorise_content_error(self, ai_processor):
        """Test error handling when categorising content."""
        ai_processor.openai_client.chat.completions.create.side_effect = Exception("Test error")
        
        with pytest.raises(Exception, match="Test error"):
            ai_processor.categorise_content("Test content")
    
    def test_summarise_content(self, ai_processor):
        """Test summarising content."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = "This is a test summary of the content."
        
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        ai_processor.openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_processor.summarise_content("Test content to summarise", max_length=100)
        
        assert result == "This is a test summary of the content."
        
        ai_processor.openai_client.chat.completions.create.assert_called_once()
    
    def test_summarise_content_error(self, ai_processor):
        """Test error handling when summarising content."""
        ai_processor.openai_client.chat.completions.create.side_effect = Exception("Test error")
        
        with pytest.raises(Exception, match="Test error"):
            ai_processor.summarise_content("Test content")
    
    def test_generate_insights(self, ai_processor):
        """Test generating insights from content."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = """
        {
            "insights": [
                "Transformer models outperform traditional RNNs by 15% on language tasks.",
                "The new architecture reduces training time by 40% while maintaining accuracy.",
                "Transfer learning techniques enable models to adapt to new domains with 70% less data."
            ]
        }
        """
        
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        ai_processor.openai_client.chat.completions.create.return_value = mock_response
        
        with patch("json.loads") as mock_loads:
            mock_loads.return_value = {
                "insights": [
                    "Transformer models outperform traditional RNNs by 15% on language tasks.",
                    "The new architecture reduces training time by 40% while maintaining accuracy.",
                    "Transfer learning techniques enable models to adapt to new domains with 70% less data."
                ]
            }
            
            result = ai_processor.generate_insights("Test content about machine learning")
            
            assert len(result) == 3
            assert "Transformer models" in result[0]
            
            ai_processor.openai_client.chat.completions.create.assert_called_once()
    
    def test_generate_insights_error(self, ai_processor):
        """Test error handling when generating insights."""
        ai_processor.openai_client.chat.completions.create.side_effect = Exception("Test error")
        
        with pytest.raises(Exception, match="Test error"):
            ai_processor.generate_insights("Test content")
    
    def test_evaluate_relevance(self, ai_processor):
        """Test evaluating content relevance."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = "0.85"
        
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        ai_processor.openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_processor.evaluate_relevance("Test content to evaluate")
        
        assert result == 0.85
        
        ai_processor.openai_client.chat.completions.create.assert_called_once()
    
    def test_evaluate_relevance_with_text(self, ai_processor):
        """Test evaluating content relevance with text response."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = "The relevance score is 0.75."
        
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        ai_processor.openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_processor.evaluate_relevance("Test content to evaluate")
        
        assert result == 0.75
        
        ai_processor.openai_client.chat.completions.create.assert_called_once()
    
    def test_evaluate_relevance_invalid_response(self, ai_processor):
        """Test evaluating content relevance with invalid response."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = "The content is relevant."
        
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        ai_processor.openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_processor.evaluate_relevance("Test content to evaluate")
        
        assert result == 0.5  # Default value
        
        ai_processor.openai_client.chat.completions.create.assert_called_once()
    
    def test_evaluate_relevance_error(self, ai_processor):
        """Test error handling when evaluating relevance."""
        ai_processor.openai_client.chat.completions.create.side_effect = Exception("Test error")
        
        with pytest.raises(Exception, match="Test error"):
            ai_processor.evaluate_relevance("Test content")
    
    def test_generate_newsletter_section(self, ai_processor):
        """Test generating a newsletter section."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = """
        
        Recent research has shown significant improvements in model efficiency...
        
        
        - Point 1
        - Point 2
        
        [Read more](https://example.com)
        """
        
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        ai_processor.openai_client.chat.completions.create.return_value = mock_response
        
        result = ai_processor.generate_newsletter_section(
            title="New ML Research",
            content="Test content about machine learning",
            category="Machine Learning",
            max_length=200
        )
        
        assert "Recent research has shown significant improvements in model efficiency" in result
        assert "- Point 1" in result
        assert "- Point 2" in result
        
        ai_processor.openai_client.chat.completions.create.assert_called_once()
    
    def test_generate_newsletter_section_error(self, ai_processor):
        """Test error handling when generating a newsletter section."""
        ai_processor.openai_client.chat.completions.create.side_effect = Exception("Test error")
        
        with pytest.raises(Exception, match="Test error"):
            ai_processor.generate_newsletter_section(
                title="Test Title",
                content="Test content",
                category="Test Category"
            )


class TestConvenienceFunctions:
    """Test cases for the convenience functions."""
    
    def test_get_ai_processor(self):
        """Test getting the AI processor singleton."""
        with patch("newsletter_generator.ai.processor.AIProcessor") as mock_processor_class:
            import newsletter_generator.ai.processor
            newsletter_generator.ai.processor.ai_processor = None
            
            processor1 = get_ai_processor()
            processor2 = get_ai_processor()
            
            assert processor1 == processor2
            mock_processor_class.assert_called_once()
    
    def test_categorise_content_function(self):
        """Test the categorise_content convenience function."""
        mock_processor = MagicMock()
        mock_processor.categorise_content.return_value = {"primary_category": "Test"}
        
        with patch("newsletter_generator.ai.processor.get_ai_processor", return_value=mock_processor):
            result = categorise_content("Test content")
            
            assert result == {"primary_category": "Test"}
            mock_processor.categorise_content.assert_called_once_with("Test content")
    
    def test_summarise_content_function(self):
        """Test the summarise_content convenience function."""
        mock_processor = MagicMock()
        mock_processor.summarise_content.return_value = "Test summary"
        
        with patch("newsletter_generator.ai.processor.get_ai_processor", return_value=mock_processor):
            result = summarise_content("Test content", max_length=150)
            
            assert result == "Test summary"
            mock_processor.summarise_content.assert_called_once_with("Test content", 150)
    
    def test_generate_insights_function(self):
        """Test the generate_insights convenience function."""
        mock_processor = MagicMock()
        mock_processor.generate_insights.return_value = ["Insight 1", "Insight 2"]
        
        with patch("newsletter_generator.ai.processor.get_ai_processor", return_value=mock_processor):
            result = generate_insights("Test content")
            
            assert result == ["Insight 1", "Insight 2"]
            mock_processor.generate_insights.assert_called_once_with("Test content")
    
    def test_evaluate_relevance_function(self):
        """Test the evaluate_relevance convenience function."""
        mock_processor = MagicMock()
        mock_processor.evaluate_relevance.return_value = 0.8
        
        with patch("newsletter_generator.ai.processor.get_ai_processor", return_value=mock_processor):
            result = evaluate_relevance("Test content")
            
            assert result == 0.8
            mock_processor.evaluate_relevance.assert_called_once_with("Test content")
    
    def test_generate_newsletter_section_function(self):
        """Test the generate_newsletter_section convenience function."""
        mock_processor = MagicMock()
        mock_processor.generate_newsletter_section.return_value = "# Test Section"
        
        with patch("newsletter_generator.ai.processor.get_ai_processor", return_value=mock_processor):
            result = generate_newsletter_section(
                title="Test Title",
                content="Test content",
                category="Test Category",
                max_length=250
            )
            
            assert result == "# Test Section"
            mock_processor.generate_newsletter_section.assert_called_once_with(
                "Test Title", "Test content", "Test Category", 250
            )


@pytest.mark.skip(reason="Requires real OpenAI API key")
class TestAIProcessorIntegration:
    """Integration tests for the AIProcessor class.
    
    These tests require a real OpenAI API key.
    They are skipped by default.
    """
    
    def test_real_categorisation(self):
        """Test categorising content with a real API call."""
        processor = AIProcessor()
        
        content = """
        
        Recent research has shown that transformer models can be optimised for better
        performance by using sparse attention mechanisms. This reduces the computational
        complexity from O(n²) to O(n log n) while maintaining similar accuracy levels.
        
        The implementation uses PyTorch and demonstrates a 40% speedup on language tasks.
        """
        
        result = processor.categorise_content(content)
        
        assert "primary_category" in result
        assert "secondary_categories" in result
        assert "tags" in result
        assert "confidence" in result
    
    def test_real_summarisation(self):
        """Test summarising content with a real API call."""
        processor = AIProcessor()
        
        content = """
        
        Transformer models have revolutionised machine learning across various domains,
        including natural language processing, computer vision, and audio processing.
        However, the standard transformer architecture has quadratic computational and
        memory complexity with respect to sequence length, which limits its application
        to long sequences.
        
        This paper surveys various approaches to improve the efficiency of transformer
        models, including sparse attention patterns, low-rank approximations, and
        kernel-based methods. We compare these approaches in terms of their theoretical
        complexity, practical speedup, and impact on model quality.
        
        Our experiments show that sparse attention mechanisms can reduce computational
        requirements by up to 80% while maintaining 95% of the original model's accuracy.
        We also provide recommendations for which efficiency techniques to use based on
        specific application requirements and hardware constraints.
        """
        
        result = processor.summarise_content(content, max_length=100)
        
        assert len(result) > 0
        assert len(result.split()) <= 120  # Allow some flexibility
    
    def test_real_insights_generation(self):
        """Test generating insights with a real API call."""
        processor = AIProcessor()
        
        content = """
        
        WebAssembly (Wasm) is a binary instruction format designed as a portable
        compilation target for high-level languages like C, C++, and Rust. It enables
        deployment of client and server applications on the web at near-native speed.
        
        Recent developments in the WebAssembly ecosystem include:
        
        1. WASI (WebAssembly System Interface) standardisation
        2. Integration with containerisation technologies
        3. Support for garbage-collected languages like Java and C#
        4. Component model for better code sharing and reuse
        
        Performance benchmarks show that WebAssembly runs at about 80-90% of native
        code speed while providing strong security guarantees through its sandboxed
        execution environment.
        """
        
        result = processor.generate_insights(content)
        
        assert len(result) > 0
    
    def test_real_relevance_evaluation(self):
        """Test evaluating relevance with a real API call."""
        processor = AIProcessor()
        
        relevant_content = """
        
        This article discusses advanced patterns for developing Kubernetes Operators
        using the Operator SDK. It covers reconciliation loops, status management,
        and handling complex state transitions in a production environment.
        """
        
        irrelevant_content = """
        
        I went to the beach this weekend. The weather was nice and I had ice cream.
        """
        
        relevant_score = processor.evaluate_relevance(relevant_content)
        irrelevant_score = processor.evaluate_relevance(irrelevant_content)
        
        assert relevant_score > irrelevant_score
        assert 0 <= relevant_score <= 1
        assert 0 <= irrelevant_score <= 1


if __name__ == "__main__":
    pytest.main()
