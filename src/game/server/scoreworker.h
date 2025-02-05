#ifndef GAME_SERVER_SCOREWORKER_H
#define GAME_SERVER_SCOREWORKER_H

#include <memory>
#include <string>
#include <utility>
#include <vector>

#include <engine/map.h>
#include <engine/server/databases/connection_pool.h>
#include <engine/shared/protocol.h>
#include <engine/shared/uuid_manager.h>
#include <game/server/save.h>
#include <game/voting.h>

class IDbConnection;
class IGameController;

enum
{
	NUM_CHECKPOINTS = 25,
	TIMESTAMP_STR_LENGTH = 20, // 2019-04-02 19:38:36
};

struct CScorePlayerResult : ISqlResult
{
	CScorePlayerResult();

	enum
	{
		MAX_MESSAGES = 10,
	};

	enum Variant
	{
		DIRECT,
		ALL,
		BROADCAST,
		MAP_VOTE,
		PLAYER_INFO,
	} m_MessageKind;
	union
	{
		char m_aaMessages[MAX_MESSAGES][512];
		char m_aBroadcast[1024];
		struct
		{
			float m_Time;
			float m_CpTime[NUM_CHECKPOINTS];
			int m_Score;
			int m_HasFinishScore;
			int m_Birthday; // 0 indicates no birthday
		} m_Info;
		struct
		{
			char m_aReason[VOTE_REASON_LENGTH];
			char m_aServer[32 + 1];
			char m_aMap[MAX_MAP_LENGTH + 1];
		} m_MapVote;
	} m_Data; // PLAYER_INFO

	void SetVariant(Variant v);
};

struct CScoreInitResult : ISqlResult
{
	CScoreInitResult() :
		m_CurrentRecord(0)
	{
	}
	float m_CurrentRecord;
};

struct CSqlInitData : ISqlData
{
	CSqlInitData(std::shared_ptr<CScoreInitResult> pResult) :
		ISqlData(std::move(pResult))
	{
	}

	// current map
	char m_aMap[MAX_MAP_LENGTH];
};

struct CSqlPlayerRequest : ISqlData
{
	CSqlPlayerRequest(std::shared_ptr<CScorePlayerResult> pResult) :
		ISqlData(std::move(pResult))
	{
	}

	// object being requested, either map (128 bytes) or player (16 bytes)
	char m_aName[MAX_MAP_LENGTH];
	// current map
	char m_aMap[MAX_MAP_LENGTH];
	char m_aRequestingPlayer[MAX_NAME_LENGTH];
	// relevant for /top5 kind of requests
	int m_Offset;
	char m_aServer[5];
};

struct CScoreRandomMapResult : ISqlResult
{
	CScoreRandomMapResult(int ClientID) :
		m_ClientID(ClientID)
	{
		m_aMap[0] = '\0';
		m_aMessage[0] = '\0';
	}
	int m_ClientID;
	char m_aMap[MAX_MAP_LENGTH];
	char m_aMessage[512];
};

struct CSqlRandomMapRequest : ISqlData
{
	CSqlRandomMapRequest(std::shared_ptr<CScoreRandomMapResult> pResult) :
		ISqlData(std::move(pResult))
	{
	}

	char m_aServerType[32];
	char m_aCurrentMap[MAX_MAP_LENGTH];
	char m_aRequestingPlayer[MAX_NAME_LENGTH];
	int m_Stars;
};

struct CSqlScoreData : ISqlData
{
	CSqlScoreData(std::shared_ptr<CScorePlayerResult> pResult) :
		ISqlData(std::move(pResult))
	{
	}

	virtual ~CSqlScoreData(){};

	char m_aMap[MAX_MAP_LENGTH];
	char m_aGameUuid[UUID_MAXSTRSIZE];
	char m_aName[MAX_MAP_LENGTH];

	int m_ClientID;
	float m_Time;
	char m_aTimestamp[TIMESTAMP_STR_LENGTH];
	float m_aCpCurrent[NUM_CHECKPOINTS];
	int m_Num;
	bool m_Search;
	char m_aRequestingPlayer[MAX_NAME_LENGTH];
};

struct CScoreSaveResult : ISqlResult
{
	CScoreSaveResult(int PlayerID, IGameController *Controller) :
		m_Status(SAVE_FAILED),
		m_SavedTeam(CSaveTeam(Controller)),
		m_RequestingPlayer(PlayerID)
	{
		m_aMessage[0] = '\0';
		m_aBroadcast[0] = '\0';
	}
	enum
	{
		SAVE_SUCCESS,
		// load team in the following two cases
		SAVE_FAILED,
		LOAD_SUCCESS,
		LOAD_FAILED,
	} m_Status;
	char m_aMessage[512];
	char m_aBroadcast[512];
	CSaveTeam m_SavedTeam;
	int m_RequestingPlayer;
	CUuid m_SaveID;
};

struct CSqlTeamScoreData : ISqlData
{
	CSqlTeamScoreData() :
		ISqlData(nullptr)
	{
	}

	char m_aGameUuid[UUID_MAXSTRSIZE];
	char m_aMap[MAX_MAP_LENGTH];
	float m_Time;
	char m_aTimestamp[TIMESTAMP_STR_LENGTH];
	unsigned int m_Size;
	char m_aaNames[MAX_CLIENTS][MAX_NAME_LENGTH];
};

struct CSqlTeamSave : ISqlData
{
	CSqlTeamSave(std::shared_ptr<CScoreSaveResult> pResult) :
		ISqlData(std::move(pResult))
	{
	}
	virtual ~CSqlTeamSave(){};

	char m_aClientName[MAX_NAME_LENGTH];
	char m_aMap[MAX_MAP_LENGTH];
	char m_aCode[128];
	char m_aGeneratedCode[128];
	char m_aServer[5];
};

struct CSqlTeamLoad : ISqlData
{
	CSqlTeamLoad(std::shared_ptr<CScoreSaveResult> pResult) :
		ISqlData(std::move(pResult))
	{
	}
	virtual ~CSqlTeamLoad(){};

	char m_aCode[128];
	char m_aMap[MAX_MAP_LENGTH];
	char m_aRequestingPlayer[MAX_NAME_LENGTH];
	int m_ClientID;
	// struct holding all player names in the team or an empty string
	char m_aClientNames[MAX_CLIENTS][MAX_NAME_LENGTH];
	int m_aClientID[MAX_CLIENTS];
	int m_NumPlayer;
};

class CPlayerData
{
public:
	CPlayerData()
	{
		Reset();
	}
	~CPlayerData() {}

	void Reset()
	{
		m_BestTime = 0;
		m_CurrentTime = 0;
		for(float &BestCpTime : m_aBestCpTime)
			BestCpTime = 0;
	}

	void Set(float Time, float CpTime[NUM_CHECKPOINTS])
	{
		m_BestTime = Time;
		m_CurrentTime = Time;
		for(int i = 0; i < NUM_CHECKPOINTS; i++)
			m_aBestCpTime[i] = CpTime[i];
	}

	float m_BestTime;
	float m_CurrentTime;
	float m_aBestCpTime[NUM_CHECKPOINTS];
};

struct CTeamrank
{
	CUuid m_TeamID;
	char m_aaNames[MAX_CLIENTS][MAX_NAME_LENGTH];
	unsigned int m_NumNames;
	CTeamrank();

	// Assumes that a database query equivalent to
	//
	//     SELECT TeamID, Name [, ...] -- the order is important
	//     FROM record_teamrace
	//     ORDER BY TeamID, Name
	//
	// was executed and that the result line of the first team member is already selected.
	// Afterwards the team member of the next team is selected.
	//
	// Returns true on SQL failure
	//
	// if another team can be extracted
	bool NextSqlResult(IDbConnection *pSqlServer, bool *pEnd, char *pError, int ErrorSize);

	bool SamePlayers(const std::vector<std::string> *pvSortedNames);
};

struct CScoreWorker
{
	static bool Init(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);

	static bool RandomMap(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool RandomUnfinishedMap(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool MapVote(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);

	static bool LoadPlayerData(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool MapInfo(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool ShowRank(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool ShowTeamRank(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool ShowTop(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool ShowTeamTop5(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool ShowPlayerTeamTop5(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool ShowTimes(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool ShowPoints(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool ShowTopPoints(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);
	static bool GetSaves(IDbConnection *pSqlServer, const ISqlData *pGameData, char *pError, int ErrorSize);

	static bool SaveTeam(IDbConnection *pSqlServer, const ISqlData *pGameData, bool Failure, char *pError, int ErrorSize);
	static bool LoadTeam(IDbConnection *pSqlServer, const ISqlData *pGameData, bool Failure, char *pError, int ErrorSize);

	static bool SaveScore(IDbConnection *pSqlServer, const ISqlData *pGameData, bool Failure, char *pError, int ErrorSize);
	static bool SaveTeamScore(IDbConnection *pSqlServer, const ISqlData *pGameData, bool Failure, char *pError, int ErrorSize);
};

#endif // GAME_SERVER_SCOREWORKER_H
