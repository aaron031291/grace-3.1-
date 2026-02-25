import { useState } from 'react';
import './SearchInternetButton.css';

/**
 * Button component that triggers auto-search when no results are found.
 * Shows loading animation while scraping websites.
 */
export default function SearchInternetButton({ query, folderPath, chatId, onSearchComplete }) {
    const [isSearching, setIsSearching] = useState(false);
    const [searchStatus, setSearchStatus] = useState('');
    const [jobIds, setJobIds] = useState([]);

    const logSystemMessage = async (content) => {
        if (!chatId) return;
        try {
            await fetch(`http://localhost:8000/chats/${chatId}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role: 'system', content: content })
            });
        } catch (e) {
            console.error("Failed to log system message", e);
        }
    };

    const handleSearchInternet = async () => {
        setIsSearching(true);
        setSearchStatus('Searching the web...');

        // Log start of search
        await logSystemMessage(`Initiating web search for: "${query}"`);

        try {
            // Build query parameters
            const params = new URLSearchParams({
                query: query,
                limit: '5',
                threshold: '0.45',
                enable_auto_search: 'true',
                folder_path: folderPath || ''
            });

            // Call the auto-search endpoint with query parameters
            const response = await fetch(`http://localhost:8000/retrieve/search-with-auto?${params}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.auto_search_triggered) {
                setJobIds(data.auto_search_job_ids || []);
                const siteCount = data.auto_search_urls?.length || 0;
                setSearchStatus(`Found ${siteCount} websites. Scraping content...`);

                await logSystemMessage(`Found ${siteCount} relevant websites. Starting scraping/ingestion...`);

                // Poll for scraping completion
                await pollScrapingStatus(data.auto_search_job_ids);

                setSearchStatus('Content scraped! Auto-ingestion will process files in 30 seconds...');

                // Wait for auto-ingestion
                setTimeout(async () => {
                    setSearchStatus('Done! You can now ask your question again.');

                    // Log completion
                    await logSystemMessage(`Web search complete. Ingested content from ${siteCount} sources. You can now re-ask your question.`);

                    setIsSearching(false);

                    // Notify parent component
                    if (onSearchComplete) {
                        onSearchComplete(data);
                    }
                }, 35000); // Wait 35 seconds for auto-ingestion
            } else {
                setSearchStatus(data.auto_search_message || 'Search failed');
                await logSystemMessage(`Web search failed: ${data.auto_search_message}`);
                setIsSearching(false);
            }
        } catch (error) {
            console.error('Auto-search error:', error);
            setSearchStatus('Error: ' + error.message);
            await logSystemMessage(`Web search error: ${error.message}`);
            setIsSearching(false);
        }
    };

    const pollScrapingStatus = async (jobIds) => {
        // ... (rest of function unchanged, just passing reference)
        if (!jobIds || jobIds.length === 0) return;

        let attempts = 0;
        const maxAttempts = 30; // 30 seconds max

        while (attempts < maxAttempts) {
            try {
                // Check status of first job (they all run together)
                const response = await fetch(`http://localhost:8000/scrape/status/${jobIds[0]}`);
                const status = await response.json();

                if (status.status === 'completed') {
                    return; // Scraping done
                } else if (status.status === 'failed') {
                    setSearchStatus('Scraping failed. Please try again.');
                    return;
                }

                // Wait 1 second before next check
                await new Promise(resolve => setTimeout(resolve, 1000));
                attempts++;
            } catch (error) {
                console.error('Error checking scraping status:', error);
                break;
            }
        }
    };

    return (
        <div className="search-internet-container">
            {!isSearching ? (
                <button
                    className="search-internet-button"
                    onClick={handleSearchInternet}
                    disabled={isSearching}
                >
                    <span className="search-icon">🌐</span>
                    Search Internet
                </button>
            ) : (
                <div className="search-internet-loading">
                    <div className="loading-spinner"></div>
                    <p className="loading-text">{searchStatus}</p>
                    {jobIds.length > 0 && (
                        <p className="loading-subtext">
                            Scraping {jobIds.length} website{jobIds.length > 1 ? 's' : ''}...
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
