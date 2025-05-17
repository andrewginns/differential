"""Task prompts v2 for the newsletter generator.

This file contains improved task prompts that follow best practices from the Google Gemini guide:
- Uses more specific and detailed instructions
- Provides clear context and constraints
- Maintains consistent structure with v1 prompts
- Assigns clear roles to the AI
- Includes examples and word limits
"""

category_prompt = "As a technical content analyst, analyze this technical content and categorize it into the appropriate primary and secondary categories, with relevant tags and a confidence score. Limit your response to a structured categorization of no more than 150 words: {content}"

summary_prompt = "As a technical content summarization specialist, create a concise, technically precise summary of this content, focusing on key technical details, methodologies, and practical applications. Keep your summary between 100-200 words: {content}"

insights_prompt = "As a technical insights specialist, extract 3-5 key technical insights from this content that would be most valuable to experienced technical professionals. Focus on novel approaches, performance improvements, and practical implementations. Limit each insight to 25 words maximum: {content}"

relevance_prompt = "As a technical content curator, evaluate the technical relevance and value of this content for inclusion in a technical newsletter. Assess its technical depth, novelty, practical applicability, accuracy, and educational value. Return only a numerical score between 0.0 and 1.0: {content}"


def section_prompt(title, category, content):
    """Generate a task prompt for creating a newsletter section.

    Args:
        title: The title of the content
        category: The category of the content
        content: The content to process

    Returns:
        The formatted task prompt
    """
    return f"""
    As a technical content editor, transform this technical content into an engaging newsletter section that highlights its most valuable aspects.
    
    Title: {title}
    Category: {category}
    
    Create a section that includes:
    1. A catchy heading related to the content
    2. A concise introduction explaining why this content matters to technical professionals
    3. A summary of the key technical points, focusing on novel approaches and practical applications
    4. A brief conclusion with implications or a call to action
    
    Format your response in proper Markdown with appropriate headings and structure.
    Keep the total section length under 300 words.
    
    Example structure:
    ```
    
    [Opening sentence on why this matters to technical professionals]
    
    [1-2 paragraphs of key technical points with the most important information first]
    
    * [Key technical detail or feature as bullet point]
    * [Another key technical detail or feature]
    
    [Brief closing sentence with call to action or future implications]
    ```
    
    Content:
    {content}
    """


def introduction_prompt(categories, total_items, content_summary=None):
    """Generate a task prompt for creating a newsletter introduction.

    Args:
        categories: List of categories in the newsletter
        total_items: Total number of content items in the newsletter
        content_summary: Optional summary of newsletter content to base introduction on

    Returns:
        The formatted task prompt
    """
    if content_summary:
        return f"""
        As an expert technical editor, create an engaging introduction for this week's technical newsletter that covers {total_items} items 
        across {len(categories)} categories: {", ".join(categories)}.
        
        Your introduction should:
        1. Welcome readers with a professional but friendly tone
        2. Highlight key themes and notable content from this week
        3. Mention the diversity of topics covered
        4. Include a brief sentence encouraging readers to explore sections that match their interests
        
        Keep your introduction under 150 words and write in a professional but conversational tone.
        
        Example tone (but with your own content):
        "Welcome to this week's tech roundup where we explore advancements in [specific areas]. This edition features [highlight something notable], alongside practical developments in [other area]. Whether you're focused on [specific domain] or exploring [another domain], you'll find valuable insights throughout. Let's dive into what's shaping our technical landscape this week."
        
        Base your introduction on this content summary:
        
        CONTENT SUMMARY:
        {content_summary}
        """
    else:
        return f"""
        As an expert technical editor, create an engaging introduction for this week's technical newsletter that covers {total_items} items 
        across {len(categories)} categories: {", ".join(categories)}.
        
        Your introduction should:
        1. Welcome readers with a professional but friendly tone
        2. Highlight the diversity of categories covered: {", ".join(categories)}
        3. Emphasize the newsletter's focus on practical, valuable technical information
        4. Include a brief sentence encouraging readers to explore sections that match their interests
        
        Keep your introduction under 150 words and write in a professional but conversational tone suitable for experienced technical professionals.
        
        Example tone (but with your own content):
        "Welcome to this week's tech roundup where we explore advancements in [specific areas]. This edition features [highlight something notable], alongside practical developments in [other area]. Whether you're focused on [specific domain] or exploring [another domain], you'll find valuable insights throughout. Let's dive into what's shaping our technical landscape this week."
        """
