/* (c) Magnus Auvinen. See licence.txt in the root of the distribution for more information. */
/* If you are missing that file, acquire a complete release at teeworlds.com.                */
#ifndef GAME_CLIENT_PREDICTION_ENTITY_H
#define GAME_CLIENT_PREDICTION_ENTITY_H

#include "gameworld.h"
#include <base/vmath.h>

#define MACRO_ALLOC_HEAP() \
public: \
	void *operator new(size_t Size) \
	{ \
		void *p = malloc(Size); \
		mem_zero(p, Size); \
		return p; \
	} \
	void operator delete(void *pPtr) \
	{ \
		free(pPtr); \
	} \
\
private:

class CEntity
{
	MACRO_ALLOC_HEAP()
	friend class CGameWorld; // entity list handling
	CEntity *m_pPrevTypeEntity;
	CEntity *m_pNextTypeEntity;

protected:
	class CGameWorld *m_pGameWorld;
	bool m_MarkedForDestroy;
	int m_ID;
	int m_ObjType;

public:
	CEntity(CGameWorld *pGameWorld, int Objtype, vec2 Pos = vec2(0, 0), int ProximityRadius = 0);
	virtual ~CEntity();

	std::vector<SSwitchers> &Switchers() { return m_pGameWorld->Switchers(); }
	class CGameWorld *GameWorld() { return m_pGameWorld; }
	CTuningParams *Tuning() { return GameWorld()->Tuning(); }
	CTuningParams *TuningList() { return GameWorld()->TuningList(); }
	CTuningParams *GetTuning(int i) { return GameWorld()->GetTuning(i); }
	class CCollision *Collision() { return GameWorld()->Collision(); }
	CEntity *TypeNext() { return m_pNextTypeEntity; }
	CEntity *TypePrev() { return m_pPrevTypeEntity; }
	float GetProximityRadius() const { return m_ProximityRadius; }

	void Destroy() { delete this; }
	virtual void Tick() {}
	virtual void TickDefered() {}

	bool GameLayerClipped(vec2 CheckPos);
	float m_ProximityRadius;
	vec2 m_Pos;
	int m_Number;
	int m_Layer;

	int m_SnapTicks;
	int m_DestroyTick;
	int m_LastRenderTick;
	CEntity *m_pParent;
	CEntity *m_pChild;
	CEntity *NextEntity() { return m_pNextTypeEntity; }
	int ID() { return m_ID; }
	void Keep()
	{
		m_SnapTicks = 0;
		m_MarkedForDestroy = false;
	}

	CEntity()
	{
		m_ID = -1;
		m_pGameWorld = 0;
	}
};

#endif
