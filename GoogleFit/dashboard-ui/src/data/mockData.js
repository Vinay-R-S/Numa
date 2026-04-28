// Rich mock data with sparklines, weekly data, and more
export const googleFitData = {
  steps: {
    value: 6842,
    unit: 'steps',
    label: 'Steps Today',
    goal: 10000,
    percentage: 68,
    sparkline: [5200, 8100, 7400, 9100, 6500, 8800, 6842],
  },
  activeMinutes: {
    value: 38,
    unit: 'min',
    label: 'Active Minutes',
    goal: 60,
    percentage: 63,
    sparkline: [22, 45, 38, 55, 30, 48, 38],
  },
  calories: {
    value: 1876,
    unit: 'kcal',
    label: 'Calories Burned',
    goal: 2500,
    percentage: 75,
    sparkline: [1600, 2200, 1900, 2400, 1700, 2100, 1876],
  },
  distance: {
    value: 5.2,
    unit: 'km',
    label: 'Distance Covered',
    goal: 8,
    percentage: 65,
    sparkline: [4.1, 6.8, 5.5, 7.2, 4.8, 6.3, 5.2],
  },
  sleep: {
    value: 6.8,
    unit: 'hrs',
    label: 'Sleep Duration',
    goal: 8,
    percentage: 85,
    sparkline: [7.2, 6.5, 8.1, 7.8, 6.2, 7.5, 6.8],
  },
  activitySegments: [
    { type: 'Walking', duration: '25 min', calories: 120, time: '08:30 AM' },
    { type: 'Running', duration: '15 min', calories: 180, time: '06:15 AM' },
    { type: 'Cycling', duration: '30 min', calories: 240, time: '05:45 PM' },
    { type: 'Yoga', duration: '20 min', calories: 80, time: '07:00 PM' }
  ],
  weeklyData: [
    { day: 'Mon', steps: 6500, calories: 1800, active: 35 },
    { day: 'Tue', steps: 9200, calories: 2300, active: 55 },
    { day: 'Wed', steps: 7400, calories: 1950, active: 42 },
    { day: 'Thu', steps: 11200, calories: 2700, active: 68 },
    { day: 'Fri', steps: 8800, calories: 2200, active: 50 },
    { day: 'Sat', steps: 5100, calories: 1600, active: 28 },
    { day: 'Sun', steps: 6842, calories: 1876, active: 38 },
  ],
};

export const stravaData = {
  activities: {
    value: 12,
    unit: 'activities',
    label: 'This Week',
    change: '+3'
  },
  distance: {
    value: 45.6,
    unit: 'km',
    label: 'Total Distance',
    change: '+12.4 km'
  },
  duration: {
    value: 4.5,
    unit: 'hrs',
    label: 'Total Duration',
    change: '+1.2 hrs'
  },
  calories: {
    value: 3420,
    unit: 'kcal',
    label: 'Calories Burned',
    change: '+840 kcal'
  },
  recentActivities: [
    {
      id: 1,
      name: 'Morning Run',
      type: 'Run',
      distance: '8.2 km',
      duration: '42 min',
      pace: '5:07 /km',
      calories: 480,
      time: '2 hours ago'
    },
    {
      id: 2,
      name: 'Evening Ride',
      type: 'Ride',
      distance: '24.5 km',
      duration: '1h 15m',
      pace: '19.6 km/h',
      calories: 620,
      time: 'Yesterday'
    },
    {
      id: 3,
      name: 'Hill Training',
      type: 'Run',
      distance: '6.4 km',
      duration: '38 min',
      pace: '5:56 /km',
      calories: 380,
      time: 'Yesterday'
    },
    {
      id: 4,
      name: 'Recovery Jog',
      type: 'Run',
      distance: '5.0 km',
      duration: '32 min',
      pace: '6:24 /km',
      calories: 290,
      time: '2 days ago'
    }
  ]
};
