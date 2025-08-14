# Game Menu Application

A beautiful Flask-based game menu application with a modern UI design featuring a left sidebar menu and a clean white main content area.

## Features

- **Modern UI Design**: Clean, responsive interface with beautiful animations
- **Left Sidebar Menu**: Three main options: Start Game, Options, and Cancel
- **Interactive Buttons**: Hover effects, animations, and sound feedback
- **Options Modal**: Configurable game settings with difficulty, sound, and volume controls
- **API Integration**: RESTful backend endpoints for game functionality
- **Responsive Design**: Works on desktop and mobile devices

## Project Structure

```
TovTech/
├── backend/
│   ├── app.py              # Main Flask application
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── templates/
│   │   └── index.html      # Main HTML template
│   └── static/
│       ├── css/
│       │   └── style.css   # Styles and animations
│       └── js/
│           └── script.js   # JavaScript functionality
└── README.md
```

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone or navigate to the project directory**
   ```bash
   cd TovTech
   ```

2. **Install Python dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Run the Flask application**
   ```bash
   python app.py
   ```

4. **Open your browser**
   Navigate to `http://localhost:5000`

## Usage

### Main Menu Options

- **Start Game**: Initiates a new game session
- **Options**: Opens a modal with game configuration settings
- **Cancel**: Cancels the current game session

### Options Configuration

The options modal allows you to configure:
- **Difficulty**: Easy, Medium, or Hard
- **Sound**: Enable/disable sound effects
- **Music Volume**: Adjust background music volume (0-100%)
- **SFX Volume**: Adjust sound effects volume (0-100%)

## API Endpoints

### Backend Routes

- `GET /` - Serves the main game page
- `POST /api/start-game` - Starts a new game
- `GET /api/options` - Retrieves current game options
- `POST /api/options` - Updates game options
- `POST /api/cancel` - Cancels the current game

## Technologies Used

- **Backend**: Flask, Flask-CORS
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Custom CSS with animations and gradients
- **Fonts**: Google Fonts (Orbitron)

## Features in Detail

### UI/UX Features
- Smooth hover animations on buttons
- Glowing text effects
- Shimmer animations on the sidebar
- Modal popups with slide-in animations
- Responsive design for mobile devices
- Sound feedback on button clicks

### Interactive Elements
- Real-time volume slider updates
- Loading states for buttons
- Success/error notifications
- Dynamic content updates

## Customization

### Adding New Menu Options
1. Add a new button in `frontend/templates/index.html`
2. Style the button in `frontend/static/css/style.css`
3. Add JavaScript functionality in `frontend/static/js/script.js`
4. Create corresponding API endpoint in `backend/app.py`

### Modifying Styles
The application uses modern CSS features including:
- CSS Grid and Flexbox for layout
- CSS Custom Properties for theming
- CSS Animations and Transitions
- Backdrop filters for glass effects

## Browser Compatibility

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Development

### Running in Development Mode
The Flask application runs in debug mode by default, which provides:
- Automatic reloading on code changes
- Detailed error messages
- Debug toolbar

### File Structure for Development
- Backend logic goes in `backend/app.py`
- Frontend templates in `frontend/templates/`
- Static assets (CSS, JS) in `frontend/static/`

## License

This project is open source and available under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues or questions, please create an issue in the repository or contact the development team.
