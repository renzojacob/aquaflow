// One colour per trip on the map and on its card. All are dark enough for white numbers.
const COLORS = ['#007067', '#7a3ff2', '#c2410c', '#1d4ed8', '#be185d', '#4d7c0f']

/** @param {number} index position of the trip in today's list */
export const tripColor = (index) => COLORS[index % COLORS.length]
