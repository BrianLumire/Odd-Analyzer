'use client';

import { useState, useEffect } from 'react';

const API_URL = '';  // empty = use relative paths
const LEAGUES = ['English', 'Spanish', 'Italian', 'German', 'Kenyan'];

const LEAGUE_COLORS = {
  English: 'bg-blue-600 hover:bg-blue-700',
  Spanish: 'bg-red-600 hover:bg-red-700',
  Italian: 'bg-green-600 hover:bg-green-700',
  German: 'bg-amber-600 hover:bg-amber-700',
  Kenyan: 'bg-purple-600 hover:bg-purple-700'
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

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/api/status`);
      const data = await res.json();
      setStatus(data.leagues || {});
    } catch (e) {
      console.error('Status fetch failed:', e);
    }
  };

  const fetchAnalysis = async (league) => {
    try {
      const res = await fetch(`${API_URL}/api/analysis?league=${league}`);
      const data = await res.json();
      if (!data.error) {
        setAnalysis((prev) => ({ ...prev, [league]: data }));
      }
    } catch (e) {
      console.error('Analysis fetch failed:', e);
    }
  };

  const scrapeLeague = async (league) => {
    setLoading((prev) => ({ ...prev, [league]: true }));
    try {
      const res = await fetch(`${API_URL}/api/scrape?league=${league}`, { method: 'POST' });
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

  const MatchItem = ({ match }) => {
    const over = match.total >= 2;
    return (
      <div className={`flex items-center gap-2 text-sm ${over ? 'text-green-700' : 'text-red-600'}`}>
        <span className="text-gray-500 w-8">W{match.week}</span>
        <span className="font-medium">{match.home} {match.hs}-{match.aws} {match.away}</span>
        <span className="ml-auto text-xs font-semibold">
          {match.total} goals {over ? '✅ O1.5' : '❌ U1.5'}
        </span>
      </div>
    );
  };

  const TargetCard = ({ target, isPrimary, week }) => {
    if (!target) return null;
    const coldStreak = target.cold_streak || false;
    const lastMatch = target.matches?.[target.matches.length - 1] || null;
    const matches = target.matches || [];

    return (
      <div className={`border rounded-lg p-4 ${isPrimary ? 'border-blue-400 bg-blue-50 shadow-md' : 'border-gray-300 bg-white shadow-sm'}`}>
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-gray-900">{target.team}</h3>
          {isPrimary && <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded-full font-semibold">🏆 Top Target</span>}
        </div>
        <div className="text-sm text-gray-600 mt-1">
          {target.played} matches · Avg Total <span className="font-bold">{target.avg_total}</span>
        </div>

        <div className="grid grid-cols-3 gap-2 mt-3 text-center">
          <div className="bg-white p-2 rounded shadow-sm">
            <div className="text-xs font-semibold text-gray-700">Avg GF</div>
            <div className="text-lg font-bold text-gray-900">{target.avg_gf}</div>
          </div>
          <div className="bg-white p-2 rounded shadow-sm">
            <div className="text-xs font-semibold text-gray-700">Avg GA</div>
            <div className="text-lg font-bold text-gray-900">{target.avg_ga}</div>
          </div>
          <div className="bg-white p-2 rounded shadow-sm">
            <div className="text-xs font-semibold text-gray-700">Avg Total</div>
            <div className="text-lg font-bold text-blue-600">{target.avg_total}</div>
          </div>
        </div>

        {matches.length > 0 && (
          <div className="mt-3">
            <div className="text-xs font-semibold text-gray-700 mb-1">📋 All matches since Week 25:</div>
            <div className="max-h-48 overflow-y-auto space-y-0.5 pr-1 bg-white/50 rounded-lg p-2">
              {matches.map((m, idx) => (
                <MatchItem key={idx} match={m} />
              ))}
            </div>
          </div>
        )}

        {coldStreak && lastMatch && !lastMatch.over ? (
          <div className="mt-3 p-3 bg-red-100 border-l-4 border-red-500 rounded text-red-800 text-sm flex items-center gap-2">
            <span className="text-lg">🚫</span>
            <span><strong>Skip next bet</strong> – Last match was Under 1.5</span>
          </div>
        ) : (
          lastMatch && lastMatch.over && (
            <div className="mt-3 p-3 bg-green-100 border-l-4 border-green-500 rounded text-green-800 text-sm flex items-center gap-2">
              <span className="text-lg">✅</span>
              <span><strong>Ready to bet</strong> – Last match was Over 1.5</span>
            </div>
          )
        )}
        {!lastMatch && (
          <div className="mt-3 p-2 bg-gray-100 rounded text-gray-500 text-sm">
            No matches from Week 25+ available.
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-block px-4 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold tracking-wider uppercase">
            🎯 Virtual Sports Intelligence
          </div>
          <h1 className="text-3xl md:text-5xl font-bold text-gray-900 mb-2 tracking-tight">
            Betika <span className="text-blue-600">Virtuals</span>
          </h1>
          <p className="text-gray-600 text-sm md:text-base">Live league dashboard &amp; Over 1.5 betting intelligence</p>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
          {LEAGUES.map((league) => {
            const week = status[league]?.current_week || '?';
            const lastScrape = getLastScrape(league);
            const isReady = typeof week === 'number' && week >= 25;
            return (
              <div key={`stat-${league}`} className="bg-white rounded-xl shadow-sm border border-gray-200 px-3 py-3 text-center">
                <div className="text-2xl">{LEAGUE_EMOJIS[league]}</div>
                <div className="text-gray-600 text-xs font-semibold uppercase tracking-wider">{league}</div>
                <div className="text-gray-900 font-bold text-lg">Week {week}</div>
                <div className="text-[10px] text-gray-400">{lastScrape}</div>
                {isReady && (
                  <div className="mt-1 text-[10px] text-green-600 font-bold">✅ Ready (25+)</div>
                )}
                {week !== '?' && week < 25 && (
                  <div className="mt-1 text-[10px] text-amber-600 font-bold">⏳ Week {week}/25</div>
                )}
              </div>
            );
          })}
        </div>

        {/* League Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 lg:gap-6">
          {LEAGUES.map((league) => {
            const isAnalyzed = analysis[league]?.top_target;
            const isLoading = loading[league] || false;
            const week = status[league]?.current_week || '?';
            const isReady = typeof week === 'number' && week >= 25;
            const data = analysis[league] || {};
            const topTarget = data.top_target || null;
            const secondaryTarget = data.secondary_target || null;

            return (
              <div
                key={league}
                className="bg-white rounded-2xl shadow-md border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow duration-200"
              >
                <div className={`h-1 w-full ${LEAGUE_COLORS[league].split(' ')[0]}`}></div>

                <div className="p-5 md:p-6">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{LEAGUE_EMOJIS[league]}</span>
                        <h2 className="text-xl font-bold text-gray-900">{league}</h2>
                        {isReady && (
                          <span className="text-[10px] bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-semibold">Ready</span>
                        )}
                        {week !== '?' && !isReady && (
                          <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-semibold">Week {week}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-500">Week {week}</span>
                        <span className="w-1 h-1 rounded-full bg-gray-300"></span>
                        <span className="text-xs text-gray-400">{getLastScrape(league)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${isLoading ? 'bg-yellow-400 animate-pulse' : 'bg-green-500'}`}></div>
                      <span className="text-[10px] text-gray-600 font-medium uppercase">{isLoading ? 'Scraping' : 'Ready'}</span>
                    </div>
                  </div>

                  {/* Scrape Button */}
                  <button
                    onClick={() => scrapeLeague(league)}
                    disabled={isLoading}
                    className={`
                      w-full py-2.5 rounded-xl font-semibold text-sm text-white transition-all duration-200
                      ${isLoading 
                        ? 'bg-gray-300 cursor-not-allowed' 
                        : `${LEAGUE_COLORS[league]} shadow-sm hover:shadow-md active:scale-[0.98]`
                      }
                    `}
                  >
                    {isLoading ? (
                      <span className="flex items-center justify-center gap-2">
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

                  {/* Analysis Results */}
                  {isAnalyzed && !isLoading && (
                    <div className="mt-4 space-y-4">
                      <TargetCard target={topTarget} isPrimary={true} week={week} />
                      {secondaryTarget && <TargetCard target={secondaryTarget} isPrimary={false} week={week} />}
                    </div>
                  )}

                  {!isAnalyzed && !isLoading && (
                    <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-200 border-dashed">
                      <p className="text-center text-gray-400 text-sm">No analysis yet. Scrape to generate insights.</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-xs text-gray-400 border-t border-gray-200 pt-6">
          <p>Virtual Sports Intelligence • Data refreshed on scrape • Over 1.5 Analysis Engine</p>
        </div>
      </div>
    </div>
  );
}