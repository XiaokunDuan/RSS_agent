import re

input_file_path = "/Users/dxk/Repos/learning/rss_agent/per_article_analysis_report_zh_optimized.md"
output_file_path = "extracted_articles.md"

article_titles_to_extract = [
    "Orchestrating Digital Resilience: A Clinical IS Study of an Everything-as-a-Service Technology Strategy",
    "Navigating Platform-Led Affiliate Marketing: Implications for Content Creation and Platform Profitability",
    "HyperCARS: Using Hyperbolic Embeddings for Generating Hierarchical Contextual Situations in Context-Aware Recommender Systems",
    "Unveiling the Cost of Free: How an Ad-Sponsored Model Affects Serialized Digital Content Creation",
    "Does Virtual Reality Help Property Sales? Empirical Evidence from a Real Estate Platform",
    "How to Make My Bug Bounty Cost-Effective? A Game-Theoretical Model",
    "Platform Governance with Algorithm-Based Content Moderation: An Empirical Study on Reddit",
    "The Effect of Voice AI on Digital Commerce",
    "Better Is Better? Signaling Paradoxes in Performance-Based Advertising",
    "Opening First-Party App Resources: Empirical Evidence of Free-Riding",
    "Timely Quality Problem Resolution in Peer-Production Systems: The Impact of Bots, Policy Citations, and Contributor Experience",
    "Mispricing and Algorithm Trading",
    "Strategic Content Generation and Monetization in Financial Social Media",
    "Enhancing User Privacy Through Ephemeral Sharing Design: Experimental Evidence from Online Dating",
    "Mobile Push vs. Pull Targeting and Geo-Conquesting",
    "Linking Clicks to Bricks: Understanding the Effects of Email Advertising on Multichannel Sales",
    "How Hospitals Differentiate Health Information Technology Portfolios for Clinical Care Efficiency: Insights from the HITECH Act",
    "Improving Students’ Argumentation Skills Using Dynamic Machine-Learning–Based Modeling",
    "Organizing for AI Innovation: Insights from an Empirical Exploration of U.S. Patents",
    "Do Digital Platforms Improve the Performance of Nonbinding Contracts? Evidence from the Amazon Freight Platform",
    "Hate Speech Detection on Online News Platforms: A Deep-Learning Approach Based on Agenda-Setting Theory",
    "Impact of Non-Diagnostic Digital Services on Online Healthcare Consultation",
    "Generative AI and its Transformative Value for Digital Platforms",
    "Heterogeneous Effects of Generative artificial intelligence (GenAI) on Knowledge Seeking in Online Communities",
    "Shifting Dynamics: How Generative AI as a Boundary Resource Reshapes Digital Platform Governance",
    "Are You Willing to Pay for Generative Artificial Intelligence (GenAI) Products? Disentangling the Disclosure Effects and the Mediating Role of Psychological Value",
    "Generative Artificial Intelligence (GenAI)-Based Recommender Addressing Contribution Pollution and Information Cacophony on Digital Platforms",
    "Complementor Value Co-Creation in Generative AI Platform Ecosystems",
    "Demystifying the Dimensions and Roles of Metaverse Gaming Experience Value: A Multi-Study Investigation",
    "Value Drivers for Metaverse Business Models: A Complementor Perspective",
    "How the Metaverse is Reshaping Multichannel Retail Through Balancing Complementarity and Substitution",
    "Everyday Metaverse: The Metaverse as an Integral Part of Everyday Life",
    "Probing Digital Footprints and Reaching for Inherent Preferences: A Cause-Disentanglement Approach to Personalized Recommendations",
    "Untangling the Performance Impact of E-marketplace Sellers’ Deployment of Platform-Based Functions: A Configurational Perspective",
    "An Explainable Artificial Intelligence Approach Using Graph Learning to Predict Intensive Care Unit Length of Stay"
]

extracted_content_blocks = []

try:
    with open(input_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Get all lines that are '##' headings and their line numbers
    all_double_hash_headings = []
    for i, line in enumerate(lines):
        if re.match(r'^##\s', line): # Regex for exactly '## ' at the beginning
            all_double_hash_headings.append((line.strip(), i))

    # Iterate through the specific titles the user wants to extract
    for target_title in article_titles_to_extract:
        start_line_for_target = -1
        # Find the starting line number for the current target title
        for heading_text, line_num in all_double_hash_headings:
            if target_title in heading_text: # Using 'in' because the heading might be '## X. Title'
                start_line_for_target = line_num
                break

        if start_line_for_target == -1:
            print(f"Warning: Target title '{target_title}' not found as a '##' heading. Skipping.")
            continue

        end_line_for_target = len(lines) # Default to end of file

        # Find the line number of the *next* '##' heading after the current target title
        # This will be the end boundary for the current article's content
        for heading_text, line_num in all_double_hash_headings:
            if line_num > start_line_for_target:
                end_line_for_target = line_num
                break

        # Extract content block
        # The content block starts from the target title's line and goes up to (but not including) the next '##' heading
        content_block = "".join(lines[start_line_for_target:end_line_for_target]).strip()
        extracted_content_blocks.append(content_block)

except FileNotFoundError:
    print(f"Error: The file '{input_file_path}' was not found.")
except Exception as e:
    print(f"An error occurred during extraction: {e}")

# Write extracted data to the output file
try:
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        if not extracted_content_blocks:
            outfile.write("No articles found or extracted.\n")
        else:
            for block in extracted_content_blocks:
                outfile.write(f"{block}\n\n---\n\n") # Add separator for readability
    print(f"Successfully extracted articles to '{output_file_path}'")
except Exception as e:
    print(f"Error writing to output file: {e}")
