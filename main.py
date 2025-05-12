from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from blockchainfolder.chain import Chain
import user_data

import utils
import sys
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables
# Use os.path.join for file paths
config_dir = os.path.join(os.path.dirname(_file_), "config")
os.makedirs(config_dir, exist_ok=True)

print("Starting Decentralised Voting System")
token = input("Create a access token: ")
orgDetails, orgNames, leaderNames, orgCodes = utils.takeOrgDetails()

if len(orgDetails.keys()) < 2:
    print("At least two organisation shoudl be registered")
    sys.exit(1)

chain = Chain(10)
userData = user_data.get_user_data()
# print(userData)
orgVoteCount: "dict[str, list[str]]" = {}
castedVoters : "list[str]" = []
print("Voting system is ready")

controller = {
    "isStarted": False,
    "isStoped": False
}


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def showHome(request: Request):
    return templates.TemplateResponse(
        "item.html", {
            "request": request
        }
    )

@app.get("/confirmation", response_class=HTMLResponse)
def showConfirmation(request: Request):
    return templates.TemplateResponse(
        "confirm.html", {
            "request": request
        }
    )

@app.get("/getOrgDetail")
def getOrgDetail():
    return {
        "orgNames": orgNames,
        "leaderNames": leaderNames,
        "orgCodes": orgCodes,
    }

@app.post("/admin/start")
def startVoting(item: utils.Token):
    if (item.token == token):
        controller["isStarted"] = True
        print("System is running: Voter can cast there vote")
        return {
            "status": "started"
        }

@app.post("/admin/stop")
def stopVoting(item: utils.Token):
    if item.token == token:
        controller["isStoped"] = True
        print("System is stoped")
        return {
            "status": "stoped"
        }

@app.post("/voter/vote")
async def CastVote(request: Request):
    formData = await request.form()
    formDict = formData._dict
    print(formData)
    print("Reached")
    print(formDict["userId"])
    print(userData.keys())
    if controller["isStarted"]:
        if formDict["userId"] in userData.keys():
            if formDict["password"] == userData[formDict["userId"]]:
                if formDict["userId"] not in castedVoters:
                    try:
                        orgName = orgDetails[formDict["orgCode"]]
                        chain.add_to_pool(orgName)
                        hash: str = chain.mine()
                        try:
                            votes = orgVoteCount[orgName]
                            votes.append(hash)
                            orgVoteCount[orgName] = votes
                        except KeyError:
                            orgVoteCount[orgName] = [hash]
                        castedVoters.append(formDict["userId"])
                        return templates.TemplateResponse(
                            "confirm.html", {
                                "request": request,
                                "status": "successfull",
                                "organisation": orgName,
                                "description": "Hash -> " + hash
                            }
                        )
                    except KeyError:
                        return templates.TemplateResponse(
                            "confirm.html", {
                                "request": request,
                                "status": "unsuccessful",
                                "description": "Invalid Organisation Details"
                            }
                        )
                else:
                    return templates.TemplateResponse(
                        "confirm.html", {
                            "request": request,
                            "status": "unsuccessful",
                            "description": "you have already casted your vote"
                        }
                    )
            else:
                return templates.TemplateResponse(
                    "confirm.html", {
                        "request": request,
                        "status": "unsuccessful",
                        "description": "wrong password"
                    }
                )
        else:
            return templates.TemplateResponse(
                "confirm.html", {
                    "request": request,
                    "status": "unsuccessful",
                    "description": "Unregistered user"
                }
            )
    else:
        return templates.TemplateResponse(
                    "confirm.html", {
                        "request": request,
                        "status": "unsuccessful",
                        "description": "Voting is closed or it is not started"
                    }
                )

@app.get("/getvotes")
def getTotalVotes():
    if not controller["isStoped"]:
        return {
            "total_votes": 0,
            "status": "Voting is currently running"
        }
    return {
        "total_votes" : len(chain.blocks)-1,
        "status": "voting has been stoped"
    }

@app.get("/getvotesbyorg")
def getVotesByOrg():
    if not controller["isStoped"]:
        return {
            "status": "Voting is currently running"
        }
    result = {}
    for i in range(len(orgVoteCount.keys())):
        org = list(orgVoteCount.keys())[i]
        count = len(list(orgVoteCount.values())[i])
        result[org] = count
    return result

if __name__ == "__main__":
    uvicorn.run(app)

