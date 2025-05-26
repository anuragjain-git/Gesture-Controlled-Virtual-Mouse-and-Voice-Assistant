#!/usr/bin/env python3
"""
Voice Assistant with Browser Automation
Combines NLP processing with Chrome tab management for conversational browser control
"""

import re
import time
from typing import Dict, Tuple, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# Constants for command recognition
COMMAND_SYNONYMS = {
    "search": ["search", "find", "look", "google", "query", "browse"],
    "open": ["open", "start", "launch", "begin", "create"],
    "close": ["close", "shut", "end", "terminate", "stop"],
    "list": ["list", "show", "display", "tabs", "windows"],
    "exit": ["exit", "quit", "goodbye", "bye", "close all"]
}

class NLPProcessor:
    """Simple NLP processor for intent recognition and entity extraction"""
    
    @staticmethod
    def extract_intent_and_entities(text: str) -> Tuple[str, Dict[str, str]]:
        """
        Extract intent and entities from natural language text
        Returns: (intent, entities_dict)
        """
        text_lower = text.lower().strip()
        intent = "unknown"
        entities = {}
        
        # Intent detection
        for command, synonyms in COMMAND_SYNONYMS.items():
            for synonym in synonyms:
                if synonym in text_lower:
                    intent = command
                    break
            if intent != "unknown":
                break
        
        # Entity extraction for search queries
        if intent == "search":
            # Extract search query after command words
            patterns = [
                r'(?:search|find|look|google|query|browse)\s+(?:for\s+)?(.+)',
                r'(.+?)(?:\s+please|\s+now)?$'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    query = match.group(1).strip()
                    if query and query != text_lower:
                        entities["query"] = query
                        break
            
            # Fallback: use entire text as query if no specific pattern matches
            if "query" not in entities:
                entities["query"] = text_lower
        
        # Entity extraction for closing tabs
        elif intent == "close":
            patterns = [
                r'close\s+(?:tab\s+)?(?:with\s+)?(.+)',
                r'shut\s+(?:down\s+)?(.+)',
                r'end\s+(.+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    keyword = match.group(1).strip()
                    entities["keyword"] = keyword
                    break
        
        return intent, entities

class ChromeTabManager:
    """Enhanced Chrome tab manager with better error handling"""
    
    def __init__(self):
        self.driver = None
        self.tabs = {}
        self.base_handle = None
        self.is_base_used = False
        self.conversation_context = []

    def start_browser(self) -> str:
        """Initialize Chrome browser"""
        try:
            if self.driver is None:
                options = Options()
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--no-first-run")
                options.add_argument("--no-default-browser-check")
                
                self.driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()), 
                    options=options
                )
                self.base_handle = self.driver.current_window_handle
                return "✅ Chrome browser started successfully!"
            else:
                return "ℹ️ Chrome is already running."
        except Exception as e:
            return f"❌ Failed to start Chrome: {str(e)}"

    def search(self, query: str) -> str:
        """Perform Google search in new or existing tab"""
        if self.driver is None:
            self.start_browser()
        
        try:
            # Store context for follow-up queries
            self.conversation_context.append(query)
            
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            if not self.is_base_used:
                self.driver.get(search_url)
                self.tabs[query] = self.base_handle
                self.is_base_used = True
            else:
                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                self.driver.get(search_url)
                self.tabs[query] = self.driver.current_window_handle
            
            # Wait for page to load
            time.sleep(2)
            return f"🔍 Searched for: '{query}'"
            
        except Exception as e:
            return f"❌ Search failed: {str(e)}"

    def contextual_search(self, new_query: str) -> str:
        """Perform search based on conversation context"""
        if self.conversation_context:
            # Combine with previous context for better results
            last_context = self.conversation_context[-1]
            enhanced_query = f"{last_context} {new_query}"
            return self.search(enhanced_query)
        else:
            return self.search(new_query)

    def list_tabs(self) -> str:
        """List all open tabs with titles"""
        if self.driver is None:
            return "❌ Chrome is not running."
        
        try:
            result = ["📋 Currently opened tabs:"]
            for i, handle in enumerate(self.driver.window_handles, 1):
                try:
                    self.driver.switch_to.window(handle)
                    title = self.driver.title or "Untitled"
                    result.append(f"  {i}. {title.strip()}")
                except:
                    result.append(f"  {i}. [Error loading tab]")
            
            return "\n".join(result) if len(result) > 1 else "📋 No tabs currently open."
            
        except Exception as e:
            return f"❌ Failed to list tabs: {str(e)}"

    def close_tab(self, keyword: str) -> str:
        """Close tab containing keyword in title"""
        if self.driver is None:
            return "❌ Chrome is not running."
        
        keyword = keyword.lower()
        
        try:
            handles = self.driver.window_handles
            for handle in handles:
                try:
                    self.driver.switch_to.window(handle)
                    title = self.driver.title.lower()
                    if keyword in title:
                        self.driver.close()
                        
                        # Switch to remaining tab
                        remaining = self.driver.window_handles
                        if remaining:
                            self.driver.switch_to.window(remaining[-1])
                            return f"✅ Closed tab: '{title}'"
                        else:
                            return f"✅ Closed last tab: '{title}'"
                            
                except Exception:
                    continue
            
            return f"❌ No tab found containing '{keyword}'"
            
        except Exception as e:
            return f"❌ Error closing tab: {str(e)}"

    def quit(self) -> str:
        """Close browser and cleanup"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                self.tabs.clear()
                self.conversation_context.clear()
                self.is_base_used = False
                return "👋 Chrome closed successfully!"
            else:
                return "ℹ️ Chrome is not running."
        except Exception as e:
            return f"❌ Error closing Chrome: {str(e)}"

class VoiceAssistant:
    """Main voice assistant class that orchestrates NLP and browser automation"""
    
    def __init__(self):
        self.nlp = NLPProcessor()
        self.browser = ChromeTabManager()
        self.conversation_history = []
    
    def process_command(self, user_input: str) -> str:
        """Process natural language command and execute appropriate action"""
        
        # Store conversation
        self.conversation_history.append(("user", user_input))
        
        # Extract intent and entities
        intent, entities = self.nlp.extract_intent_and_entities(user_input)
        
        print(f"[DEBUG] Intent: {intent}, Entities: {entities}")
        
        # Execute based on intent
        response = ""
        
        if intent == "search":
            query = entities.get("query", user_input)
            
            # Check for contextual follow-up
            # if any(word in query for word in ["good", "best", "rated", "recommended", "popular", "with"]):
            response = self.browser.contextual_search(query)
            # else:
            #     response = self.browser.search(query)
                
        elif intent == "open":
            response = self.browser.start_browser()
            
        elif intent == "list":
            response = self.browser.list_tabs()
            
        elif intent == "close":
            keyword = entities.get("keyword", "")
            if keyword:
                response = self.browser.close_tab(keyword)
            else:
                response = "❓ Please specify which tab to close (e.g., 'close google')"
                
        elif intent == "exit":
            response = self.browser.quit()
            
        else:
            response = self._handle_unknown_command(user_input)
        
        # Store response
        self.conversation_history.append(("assistant", response))
        return response
    
    def _handle_unknown_command(self, user_input: str) -> str:
        """Handle unrecognized commands with helpful suggestions"""
        suggestions = [
            "🤔 I didn't understand that command. Here's what I can help with:",
            "• Search: 'search for restaurants in New York'",
            "• List tabs: 'show me all tabs'", 
            "• Close tab: 'close the google tab'",
            "• Exit: 'quit' or 'goodbye'"
        ]
        return "\n".join(suggestions)
    
    def run_interactive_mode(self):
        """Run interactive chat mode"""
        print("🤖 Voice Assistant Started!")
        print("Type 'quit' or 'exit' to stop\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                    response = self.browser.quit()
                    print(f"Assistant: {response}")
                    break
                
                response = self.process_command(user_input)
                print(f"Assistant: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                self.browser.quit()
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}\n")

def main():
    """Main entry point"""
    assistant = VoiceAssistant()
    
    print("=" * 50)
    print("🎯 VOICE ASSISTANT WITH BROWSER AUTOMATION")
    print("=" * 50)
    print("Commands you can try:")
    print("• 'search for restaurants in New York'")
    print("• 'how about ones with good ratings'")
    print("• 'show me all tabs'")
    print("• 'close the google tab'")
    print("• 'quit'")
    print("=" * 50)
    
    assistant.run_interactive_mode()

if __name__ == "__main__":
    main()