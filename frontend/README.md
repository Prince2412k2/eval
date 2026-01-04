# Policy Chatbot Frontend

Beautiful, minimal frontend for the Policy Chatbot with streaming responses, citations, and conversation history.

## Features

- ✨ **Streaming Responses**: Real-time token-by-token streaming from the LLM
- 📚 **Citations Display**: Shows source citations with document name, page, section, and text spans
- 📄 **Source Documents**: Links to original policy documents
- 💬 **Conversation Continuity**: Maintains conversation context across messages
- 🎨 **Modern UI**: Glassmorphism effects, gradient backgrounds, smooth animations
- 📱 **Responsive**: Works on desktop and mobile

## Tech Stack

- React 19
- TypeScript
- Tailwind CSS v4
- Vite

## Getting Started

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

## API Integration

The frontend connects to the backend API at `http://localhost:8000`:

- `POST /api/query` - Send queries and receive streaming responses
- `GET /api/conversations/{id}` - Get conversation history
- `DELETE /api/conversations/{id}` - Delete conversation

## Features Breakdown

### Streaming Chat Interface

- Real-time message streaming using Server-Sent Events (SSE)
- Smooth animations for message appearance
- Auto-scroll to latest message

### Citations Display

Each assistant response includes:
- Document name and page number
- Section hierarchy
- Text span (50-200 chars from source)
- Citation type (direct quote, paraphrase, inference)

### Conversation Management

- Automatic conversation creation on first message
- Conversation ID tracking for follow-up questions
- Context maintained across messages

## Customization

### Colors

Edit the gradient in `App.css`:

```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### API Endpoint

Change the API URL in `App.tsx`:

```typescript
const response = await fetch('http://localhost:8000/api/query', {
  // ...
});
```

## Future Enhancements

- Conversation history sidebar
- Document upload UI
- Dark/light mode toggle
- Export conversation
- Citation verification UI
