"""Task prompts v1 for the newsletter generator."""

category_prompt = "Please categorise the following technical content: {content}"

summary_prompt = "Please summarise the following technical content: {content}"

insights_prompt = "Please extract key technical insights from the following content: {content}"

relevance_prompt = "Please evaluate the technical relevance of the following content: {content}"


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
    Please create a newsletter section for the following technical content:
    
    Title: {title}
    Category: {category}
    
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
        This week's technical newsletter includes {total_items} items across {len(categories)} categories:
        {", ".join(categories)}.
        
        Based on the following newsletter content summary, please generate an engaging introduction that 
        highlights key themes and important items from this week's content.
        
        CONTENT SUMMARY:
        {content_summary}
        """
    else:
        return f"""
        This week's technical newsletter includes {total_items} items across {len(categories)} categories:
        {", ".join(categories)}.
        
        Please generate an engaging introduction for a technical newsletter that highlights
        the diversity of content and encourages readers to explore the different sections.
        """
