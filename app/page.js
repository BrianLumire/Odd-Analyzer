'use client';

import { useState, useEffect } from 'react';

const API_URL = '';
const LEAGUES = ['English', 'Spanish', 'Italian', 'German', 'Kenyan'];

const LEAGUE_COLORS = {
  English: 'from-blue-500 to-blue-700',
  Spanish: 'from-red-500 to-red-700',
  Italian: 'from-green-500 to-green-700',
  German: 'from-amber-500 to-amber-700',
  Kenyan: 'from-purple-500 to-purple-700'
};

const LEAGUE_EMOJIS = {
  English: '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  Spanish: '🇪🇸',
  Italian: '🇮🇹',
  German: '🇩🇪',
  Kenyan: '🇰🇪'
};

export default function Home() {
  const [status, setStatus] = useState({});
  const [loading, setLoading] = useState({});
  const [analysis, setAnalysis] = useState({});
  const [stake, setStake] = useState(5000);
  const [selectedTeams, setSelectedTeams] = useState({});

  const fetchStatus = async () => {
    try {
      const res = await fetch(`/api/status`);
      const data = await res.json();
      setStatus(data.leagues || {});
    } catch (e) {
      console.error('Status fetch failed:', e);
    }
  };

  const fetchAnalysis = async (league) => {
    try {
      const res = await fetch(`/api/analysis?league=${league}`);
      const data = await res.json();
      if (!data.error) {
        setAnalysis((prev) => ({ ...prev, [league]: data }));
        const targets = data.targets || [];
        const initialSelections = {};
        targets.forEach((t) => {
          initialSelections[t.team] = t.recommendation === 'Bet';
        });
        setSelectedTeams((prev) => ({ ...prev, [league]: initialSelections }));
      }
    } catch (e) {
      console.error('Analysis fetch failed:', e);
    }
  };

  const scrapeLeague = async (league) => {
    setLoading((prev) => ({ ...prev, [league]: true }));
    try {
      const res = await fetch(`/api/scrape?league=${league}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        await fetchStatus();
        await fetchAnalysis(league);
      } else {
        console.error('Scrape error:', data.error);
      }
    } catch (e) {
      console.error('Scrape request failed:', e);
    }
    setLoading((prev) => ({ ...prev, [league]: false }));
  };

  useEffect(() => {
    fetchStatus();
    LEAGUES.forEach(fetchAnalysis);
  }, []);

  const getLastScrape = (league) => {
    if (!status[league]?.last_scrape) return 'Never';
    const date = new Date(status[league].last_scrape);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000 / 60);
    if (diff < 1) return 'Just now';
    if (diff < 60) return `${diff}m ago`;
    return `${Math.floor(diff / 60)}h ago`;
  };

  const calculateAccumulator = (league) => {
    const targets = analysis[league]?.targets || [];
    const selected = targets.filter(
      (t) => selectedTeams[league]?.[t.team] && t.current_odds !== null && t.current_odds !== undefined
    );
    const odds = selected.map((t) => t.current_odds);
    const count = odds.length;

    if (count < 2) {
      return {
        count,
        baseCombined: null,
        boostPercent: 0,
        boostedOdds: null,
        potentialWin: null,
        boostAmount: null,
        selected,
        message: count === 0 ? 'Select at least 2 teams' : 'Select 1 more team',
      };
    }

    const baseCombined = odds.reduce((a, b) => a * b, 1);
    const boostPercent = count === 2 ? 0.05 : 0.10;
    const boostedOdds = baseCombined * (1 + boostPercent);
    const potentialWin = stake * boostedOdds;
    const boostAmount = potentialWin - stake * baseCombined;

    return {
      count,
      baseCombined,
      boostPercent,
      boostedOdds,
      potentialWin,
      boostAmount,
      selected,
      message: null,
    };
  };

  const MatchItem = ({ match }) => {
    const over = match.total >= 2;
    return (
      <div className={`flex items-center gap-2 text-sm ${over ? 'text-emerald-400' : 'text-red-400'}`}>
        <span className="text-slate-500 w-8">W{match.week}</span>
        <span className="font-medium text-slate-200">
          {match.home} {match.hs}-{match.aws} {match.away}
        </span>
        <span className="ml-auto text-xs font-semibold">
          {match.total} goals {over ? '✅ O1.5' : '❌ U1.5'}
        </span>
      </div>
    );
  };

  const TargetCard = ({ target, isPrimary, week, league, onToggle }) => {
    if (!target) return null;
    const coldStreak = target.cold_streak || false;
    const lastMatch = target.matches?.[target.matches.length - 1] || null;
    const matches = target.matches || [];
    const seasonType = target.season_type || 'unknown';
    const seasonWeeks = target.season_weeks || '?';
    const team = target.team;
    const odds = target.current_odds;
    const recommendation = target.recommendation || 'N/A';
    const isSelected = selectedTeams[league]?.[team] || false;

    const singleWin = odds !== null && odds !== undefined ? stake * odds : null;
    const singleProfit = singleWin !== null ? singleWin - stake : null;

    const getRecommendationColor = () => {
      if (recommendation === 'Bet') return 'bg-emerald-600 text-white';
      if (recommendation === 'Skip') return 'bg-red-600 text-white';
      return 'bg-slate-600 text-slate-300';
    };

    return (
      <div
        className={`border rounded-lg p-4 ${
          isPrimary
            ? 'border-blue-500 bg-slate-800 shadow-lg shadow-blue-500/10'
            : 'border-slate-700 bg-slate-800/60'
        }`}
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xl font-bold text-white">{team}</h3>
              {isPrimary && (
                <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded-full font-semibold">🏆 Top</span>
              )}
            </div>
            <div className="text-sm text-slate-400 mt-1">
              {target.played} matches · Avg Total <span className="font-bold text-white">{target.avg_total}</span>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-semibold ${getRecommendationColor()}`}
            >
              {recommendation}
            </span>
            <label className="flex items-center gap-1 text-xs text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onToggle(team)}
                disabled={odds === null || odds === undefined}
                className="w-4 h-4 accent-blue-500 cursor-pointer disabled:opacity-30"
              />
              Include
            </label>
          </div>
        </div>

        {/* Stats grid – UPDATED with bigger, blue "All" hit rate */}
        <div className="grid grid-cols-4 gap-2 mt-3 text-center">
          <div className="bg-slate-700/50 p-2 rounded">
            <div className="text-[10px] font-semibold text-slate-400">Avg GF</div>
            <div className="text-lg font-bold text-white">{target.avg_gf}</div>
          </div>
          <div className="bg-slate-700/50 p-2 rounded">
            <div className="text-[10px] font-semibold text-slate-400">Avg GA</div>
            <div className="text-lg font-bold text-white">{target.avg_ga}</div>
          </div>
          <div className="bg-slate-700/50 p-2 rounded">
            <div className="text-[10px] font-semibold text-slate-400">Avg Total</div>
            <div className="text-lg font-bold text-blue-400">{target.avg_total}</div>
          </div>
          <div className="bg-slate-700/50 p-2 rounded">
            <div className="text-[10px] font-semibold text-slate-400">Hit Rate</div>
            <div className="text-lg font-bold text-yellow-400">{target.hit_rate}%</div>
            <div className="text-sm font-semibold text-blue-400">All: {target.hit_rate_all}%</div>
          </div>
        </div>

        {/* Odds & Win */}
        <div className="mt-3 flex items-center justify-between bg-slate-900/50 rounded-lg p-2">
          <div>
            <span className="text-xs text-slate-400">Current Odds</span>
            <div className="font-bold text-white text-lg">
              {odds !== null && odds !== undefined ? odds.toFixed(2) : 'N/A'}
            </div>
          </div>
          {odds !== null && odds !== undefined && (
            <div className="text-right">
              <span className="text-xs text-slate-400">Single Bet (Stake {stake} KES)</span>
              <div className="text-emerald-400 font-bold">
                Win: {singleWin.toFixed(2)} KES
                <span className="text-green-300 text-xs ml-2">
                  (+{singleProfit.toFixed(2)})
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Matches */}
        {matches.length > 0 && (
          <div className="mt-3">
            <div className="text-xs font-semibold text-slate-400 mb-1">📋 All matches :</div>
            <div className="max-h-48 overflow-y-auto space-y-0.5 pr-1 bg-slate-900/50 rounded-lg p-2">
              {matches.map((m, idx) => (
                <MatchItem key={idx} match={m} />
              ))}
            </div>
          </div>
        )}

        {/* Cold streak warning */}
        {coldStreak && lastMatch && !lastMatch.over && (
          <div className="mt-3 p-2 bg-red-900/30 border-l-4 border-red-500 rounded text-red-300 text-sm flex items-center gap-2">
            <span>🚫</span>
            <span>
              <strong>Skip next bet</strong> – Last match was Under 1.5
            </span>
          </div>
        )}
        {!coldStreak && lastMatch && lastMatch.over && (
          <div className="mt-3 p-2 bg-emerald-900/30 border-l-4 border-emerald-500 rounded text-emerald-300 text-sm flex items-center gap-2">
            <span>✅</span>
            <span>
              <strong>Ready to bet</strong> – Last match was Over 1.5
            </span>
          </div>
        )}
      </div>
    );
  };

  const AccumulatorPreview = ({ league }) => {
    const acc = calculateAccumulator(league);
    if (!acc || acc.count < 2) {
      return (
        <div className="mt-4 p-4 bg-slate-700/30 rounded-xl border border-slate-700 border-dashed text-center">
          <p className="text-slate-400 text-sm">{acc?.message || 'Select at least 2 teams with odds to see accumulator'}</p>
        </div>
      );
    }

    return (
      <div className="mt-4 p-4 bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl border border-yellow-500/30 shadow-lg shadow-yellow-500/5">
        <h4 className="text-sm font-semibold text-yellow-400 uppercase tracking-wider flex items-center gap-2">
          📊 Accumulator ({acc.count} selections)
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2 text-center">
          <div className="bg-slate-700/50 p-2 rounded">
            <div className="text-[10px] text-slate-400">Base Odds</div>
            <div className="text-white font-bold">{acc.baseCombined.toFixed(3)}</div>
          </div>
          <div className="bg-slate-700/50 p-2 rounded">
            <div className="text-[10px] text-slate-400">Boost</div>
            <div className="text-emerald-400 font-bold">+{(acc.boostPercent * 100).toFixed(0)}%</div>
          </div>
          <div className="bg-slate-700/50 p-2 rounded">
            <div className="text-[10px] text-slate-400">Boosted Odds</div>
            <div className="text-yellow-400 font-bold">{acc.boostedOdds.toFixed(3)}</div>
          </div>
          <div className="bg-slate-700/50 p-2 rounded">
            <div className="text-[10px] text-slate-400">Win (Stake {stake} KES)</div>
            <div className="text-emerald-400 font-bold">{acc.potentialWin.toFixed(2)} KES</div>
            <div className="text-[10px] text-green-300">
              Boost: +{acc.boostAmount.toFixed(2)} KES
            </div>
          </div>
        </div>
        <div className="mt-2 text-xs text-slate-500 text-center">
          Teams: {acc.selected.map((t) => t.team).join(', ')}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-900 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <div className="inline-block px-4 py-1 bg-blue-900/50 text-blue-300 rounded-full text-xs font-semibold tracking-wider uppercase border border-blue-700">
            🎯 Virtual Sports Intelligence
          </div>
          <h1 className="text-3xl md:text-5xl font-bold text-white mb-2 tracking-tight">
            Sport <span className="text-blue-400">Virtuals</span>
          </h1>
          <p className="text-slate-400 text-sm md:text-base">Live league dashboard &amp; Over 1.5 betting intelligence</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
          {LEAGUES.map((league) => {
            const week = status[league]?.current_week || '?';
            const lastScrape = getLastScrape(league);
            const isReady = typeof week === 'number' && week >= 18;
            return (
              <div key={`stat-${league}`} className="bg-slate-800/80 rounded-xl shadow-lg border border-slate-700 px-3 py-3 text-center">
                <div className="text-2xl">{LEAGUE_EMOJIS[league]}</div>
                <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider">{league}</div>
                <div className="text-white font-bold text-lg">Week {week}</div>
                <div className="text-[10px] text-slate-500">{lastScrape}</div>
                {isReady && <div className="mt-1 text-[10px] text-emerald-400 font-bold">✅ Ready (18+)</div>}
                {week !== '?' && week < 18 && (
                  <div className="mt-1 text-[10px] text-amber-400 font-bold">⏳ Week {week}/18</div>
                )}
              </div>
            );
          })}
        </div>

        {LEAGUES.map((league) => {
          const isAnalyzed = analysis[league]?.top_target;
          const isLoading = loading[league] || false;
          const week = status[league]?.current_week || '?';
          const isReady = typeof week === 'number' && week >= 18;
          const data = analysis[league] || {};
          const targets = data.targets || [];

          const handleToggle = (team) => {
            setSelectedTeams((prev) => ({
              ...prev,
              [league]: {
                ...(prev[league] || {}),
                [team]: !(prev[league]?.[team] || false),
              },
            }));
          };

          return (
            <div
              key={league}
              className="bg-slate-800/90 rounded-2xl shadow-xl border border-slate-700 overflow-hidden hover:border-slate-500 transition-all duration-200 mb-6"
            >
              <div className={`h-1 w-full bg-gradient-to-r ${LEAGUE_COLORS[league]}`}></div>

              <div className="p-5 md:p-6">
                <div className="flex flex-wrap items-start justify-between mb-4 gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{LEAGUE_EMOJIS[league]}</span>
                      <h2 className="text-xl font-bold text-white">{league}</h2>
                      {isReady && (
                        <span className="text-[10px] bg-emerald-900/50 text-emerald-400 px-2 py-0.5 rounded-full font-semibold border border-emerald-700">
                          Ready
                        </span>
                      )}
                      {week !== '?' && !isReady && (
                        <span className="text-[10px] bg-amber-900/50 text-amber-400 px-2 py-0.5 rounded-full font-semibold border border-amber-700">
                          Week {week}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-slate-400">Week {week}</span>
                      <span className="w-1 h-1 rounded-full bg-slate-600"></span>
                      <span className="text-xs text-slate-500">{getLastScrape(league)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${isLoading ? 'bg-yellow-400 animate-pulse' : 'bg-emerald-400'}`}></div>
                    <span className="text-[10px] text-slate-400 font-medium uppercase">{isLoading ? 'Scraping' : 'Ready'}</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 mb-4">
                  <div className="flex items-center gap-2 bg-slate-700/50 rounded-lg px-3 py-1.5 border border-slate-600">
                    <span className="text-xs text-slate-400 font-semibold">Stake (KES)</span>
                    <input
                      type="number"
                      value={stake}
                      onChange={(e) => setStake(parseFloat(e.target.value) || 0)}
                      className="w-24 bg-transparent text-white font-bold text-sm focus:outline-none"
                      min="100"
                      step="100"
                    />
                  </div>
                  <button
                    onClick={() => scrapeLeague(league)}
                    disabled={isLoading}
                    className={`
                      py-2 px-4 rounded-xl font-semibold text-sm text-white transition-all duration-200
                      ${isLoading
                        ? 'bg-slate-700 cursor-not-allowed'
                        : `bg-gradient-to-r ${LEAGUE_COLORS[league]} shadow-lg hover:shadow-xl active:scale-[0.98]`
                      }
                    `}
                  >
                    {isLoading ? (
                      <span className="flex items-center gap-2">
                        <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Scraping...
                      </span>
                    ) : (
                      '⟳ Scrape Now'
                    )}
                  </button>
                </div>

                {isAnalyzed && !isLoading && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {targets.slice(0, 4).map((target, index) => (
                        <TargetCard
                          key={target.team}
                          target={target}
                          isPrimary={index === 0}
                          week={week}
                          league={league}
                          onToggle={handleToggle}
                        />
                      ))}
                    </div>
                    <AccumulatorPreview league={league} />
                  </div>
                )}

                {!isAnalyzed && !isLoading && (
                  <div className="mt-4 p-4 bg-slate-700/30 rounded-xl border border-slate-700 border-dashed">
                    <p className="text-center text-slate-400 text-sm">No analysis yet. Scrape to generate insights.</p>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        <div className="mt-8 text-center text-xs text-slate-500 border-t border-slate-800 pt-6">
          <p>Virtual Sports Intelligence • Data refreshed on scrape • Over 1.5 Analysis Engine</p>
        </div>
      </div>
    </div>
  );
}